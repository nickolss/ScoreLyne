"""Treino do modelo na população sintética da operadora mock.

Os fatores são calculados exatamente como em produção: a partir da visão que a operadora
entrega ao banco (`montar_dados`), com todos os escopos autorizados.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split

from scorelyne.operadora.generator import gerar_populacao
from scorelyne.operadora.models import Escopo
from scorelyne.operadora.store import montar_dados

from . import politica
from .fatores import ORDEM, StatusFator, calcular_fatores
from .modelo import Modelo, nova_versao, pontuar

REGIOES = {
    "Norte": {"AM", "PA", "AC", "RO", "RR", "AP", "TO"},
    "Nordeste": {"BA", "PE", "CE", "MA", "PI", "RN", "PB", "AL", "SE"},
    "Centro-Oeste": {"GO", "DF", "MT", "MS"},
    "Sudeste": {"SP", "RJ", "MG", "ES"},
    "Sul": {"RS", "PR", "SC"},
}


# Um grupo está calibrado se a PD prevista cai dentro do intervalo de 95% da inadimplência observada
# (±1,96 erro-padrão). Grupos pequenos têm ruído amostral maior, então a margem acompanha o tamanho.
Z_95 = 1.96


def regiao(uf: str) -> str:
    return next(nome for nome, ufs in REGIOES.items() if uf in ufs)


def montar_base(tamanho: int, semente: int):
    linhas, fatores, rotulos = [], [], []
    for linha, perfil in gerar_populacao(tamanho, semente):
        dados = montar_dados(linha, list(Escopo), "treino")
        linhas.append(linha)
        fatores.append(calcular_fatores(dados))
        rotulos.append(int(perfil.inadimplente))
    return linhas, fatores, np.array(rotulos)


def matriz(fatores_por_linha, medias: dict[Escopo, float] | None = None) -> np.ndarray:
    x = np.full((len(fatores_por_linha), len(ORDEM)), np.nan)
    for i, fatores in enumerate(fatores_por_linha):
        for j, f in enumerate(fatores):
            if f.status is StatusFator.CALCULADO:
                x[i, j] = f.valor
    if medias is not None:
        for j, k in enumerate(ORDEM):
            x[np.isnan(x[:, j]), j] = medias[k]
    return x


def ajustar_monotonico(x: np.ndarray, y: np.ndarray) -> tuple[dict[Escopo, float], float]:
    """Regressão logística em que todo fator só pode reduzir o risco quando melhora.

    Um fator com sinal invertido (ex.: trocar de chip aumentaria o score) sai do modelo e é
    reajustado sem ele. O fator continua aparecendo na análise, com peso zero.
    """
    ativos = list(range(len(ORDEM)))
    while True:
        reg = LogisticRegression(C=10.0, max_iter=1000).fit(x[:, ativos], y)
        invertidos = [j for j, w in zip(ativos, reg.coef_[0], strict=True) if w > 0]
        if not invertidos:
            break
        ativos = [j for j in ativos if j not in invertidos]
    coefs = dict.fromkeys(ORDEM, 0.0)
    for j, w in zip(ativos, reg.coef_[0], strict=True):
        coefs[ORDEM[j]] = float(w)
    return coefs, float(reg.intercept_[0])


def ks(y: np.ndarray, p: np.ndarray) -> float:
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr - fpr))


def treinar(tamanho: int = 3000, semente: int = 42) -> Modelo:
    linhas, fatores, y = montar_base(tamanho, semente)
    idx_treino, idx_teste = train_test_split(
        np.arange(len(y)), test_size=0.3, stratify=y, random_state=semente
    )

    bruto = matriz([fatores[i] for i in idx_treino])
    medias = {k: float(np.nanmean(bruto[:, j])) for j, k in enumerate(ORDEM)}
    x_treino = matriz([fatores[i] for i in idx_treino], medias) / 100
    x_teste = matriz([fatores[i] for i in idx_teste], medias) / 100

    coefs, intercepto = ajustar_monotonico(x_treino, y[idx_treino])
    ativos = [j for j, k in enumerate(ORDEM) if coefs[k] != 0]

    # Sem dado, sem benefício: o fator não autorizado entra com o pior valor observado,
    # então omitir um escopo opcional nunca aumenta o score.
    conservador = {k: float(np.nanmin(bruto[:, j])) for j, k in enumerate(ORDEM)}
    desvios = x_treino.std(axis=0)
    peso = {k: abs(coefs[k]) * desvios[j] for j, k in enumerate(ORDEM)}
    total = sum(peso.values())

    w = np.array([coefs[k] for k in ORDEM])
    p_teste = 1 / (1 + np.exp(-(intercepto + x_teste @ w)))
    auc = float(roc_auc_score(y[idx_teste], p_teste))

    modelo = Modelo(
        versao=nova_versao(semente),
        treinado_em=datetime.now(UTC),
        intercepto=intercepto,
        coeficientes=coefs,
        medias={k: round(v, 3) for k, v in medias.items()},
        conservador={k: round(v, 3) for k, v in conservador.items()},
        importancia={k: round(v / total, 4) for k, v in peso.items()},
        metricas={
            "auc": round(auc, 4),
            "gini": round(2 * auc - 1, 4),
            "ks": round(ks(y[idx_teste], p_teste), 4),
            "taxa_inadimplencia": round(float(y.mean()), 4),
            "n_treino": len(idx_treino),
            "n_teste": len(idx_teste),
            "fatores_ativos": len(ativos),
        },
    )
    # Equidade na base inteira: com 5 parâmetros não há sobreajuste relevante, e grupos maiores
    # reduzem o ruído amostral das taxas por região.
    modelo.equidade = avaliar_equidade(modelo, linhas, fatores, y)
    modelo.metricas.update(avaliar_politica(modelo, [fatores[i] for i in idx_teste], y[idx_teste]))
    return modelo


def _decisoes(modelo: Modelo, fatores_por_linha) -> list[politica.Decisao]:
    return [politica.decisao_pelo_score(pontuar(f, modelo).score) for f in fatores_por_linha]


def avaliar_politica(modelo: Modelo, fatores_por_linha, y: np.ndarray) -> dict[str, float]:
    decisoes = _decisoes(modelo, fatores_por_linha)
    aprovados = [i for i, d in enumerate(decisoes) if d is politica.Decisao.APROVADO]
    recusados = [i for i, d in enumerate(decisoes) if d is politica.Decisao.RECUSADO]
    n = len(decisoes)
    return {
        "taxa_aprovacao_automatica": round(len(aprovados) / n, 4),
        "taxa_revisao": round(sum(d is politica.Decisao.REVISAO for d in decisoes) / n, 4),
        "taxa_recusa": round(len(recusados) / n, 4),
        "inadimplencia_aprovados": round(float(y[aprovados].mean()), 4) if aprovados else 0.0,
        "inadimplencia_recusados": round(float(y[recusados].mean()), 4) if recusados else 0.0,
    }


def avaliar_equidade(modelo: Modelo, linhas, fatores_por_linha, y: np.ndarray) -> dict:
    """Taxa de aprovação automática por grupo e razão de impacto (regra dos 4/5).

    Região e plano não entram no modelo; o teste verifica se vazam pelos fatores. A
    inadimplência entre aprovados por grupo mostra se o mesmo padrão de risco vale para todos.

    Quando a razão de impacto falha mas o modelo está calibrado em todos os grupos, a diferença
    de aprovação reflete diferença de risco ou de informação (ex.: só o pré-pago tem o fator de
    recargas), e não um erro do modelo contra um grupo. Os dois sinais saem juntos de propósito.
    """
    decisoes = _decisoes(modelo, fatores_por_linha)
    pds = np.array([pontuar(f, modelo).probabilidade_inadimplencia for f in fatores_por_linha])
    resultado = {}
    for nome, chave in (("regiao", lambda l: regiao(l.uf)), ("plano", lambda l: l.plano.value)):
        grupos: dict[str, list[int]] = defaultdict(list)
        for i, linha in enumerate(linhas):
            grupos[chave(linha)].append(i)
        taxas = {}
        for grupo, idx in sorted(grupos.items()):
            aprovados = [i for i in idx if decisoes[i] is politica.Decisao.APROVADO]
            taxas[grupo] = {
                "n": len(idx),
                "taxa_aprovacao": round(len(aprovados) / len(idx), 4),
                "inadimplencia_real": round(float(y[idx].mean()), 4),
                # Calibração: a probabilidade prevista deve acompanhar a inadimplência real do grupo.
                "pd_prevista": round(float(pds[idx].mean()), 4),
                # Mesmo padrão de risco para todos: inadimplência parecida entre os aprovados.
                "inadimplencia_aprovados": round(float(y[aprovados].mean()), 4) if aprovados else None,
            }
        aprov = [t["taxa_aprovacao"] for t in taxas.values() if t["n"] >= 30]
        razao = round(min(aprov) / max(aprov), 4) if aprov and max(aprov) > 0 else None
        for t in taxas.values():
            p = t["inadimplencia_real"]
            t["margem_95"] = round(Z_95 * math.sqrt(p * (1 - p) / t["n"]), 4)
            t["calibrado"] = abs(t["pd_prevista"] - p) <= t["margem_95"]
        grandes = [t for t in taxas.values() if t["n"] >= 30]
        erros = [abs(t["pd_prevista"] - t["inadimplencia_real"]) for t in grandes]
        resultado[nome] = {
            "grupos": taxas,
            "razao_impacto": razao,
            "passa_regra_4_5": bool(razao and razao >= 0.8),
            "erro_calibracao_maximo": round(max(erros), 4) if erros else None,
            "calibrado_em_todos_os_grupos": bool(grandes and all(t["calibrado"] for t in grandes)),
        }
    return resultado
