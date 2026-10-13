"""Análise completa de uma linha: fatores → score → decisão → oferta → explicação."""

from __future__ import annotations

from pydantic import BaseModel

from scorelyne.operadora.models import DadosLinha

from . import politica
from .fatores import ROTULOS, Fator, StatusFator, calcular_fatores
from .modelo import Modelo, carregar_modelo, pontuar


class FatorExplicado(Fator):
    pontos: float  # contribuição para o score, positiva ou negativa
    valor_usado: float  # valor que entrou no modelo, depois de imputação


class EscoposObrigatoriosAusentes(ValueError):
    pass


class ResultadoAnalise(BaseModel):
    telefone: str
    score: int
    faixa: str
    decisao: politica.Decisao
    decisao_pelo_score: politica.Decisao
    confianca: politica.Confianca
    probabilidade_inadimplencia: float
    pontos_base: float
    fatores: list[FatorExplicado]
    pontos_fortes: list[str]
    pontos_de_atencao: list[str]
    motivos_revisao: list[str]
    plano_de_melhora: list[str]
    oferta: politica.Oferta | None
    modelo_versao: str


def analisar(
    dados: DadosLinha, valor_solicitado: float | None = None, modelo: Modelo | None = None
) -> ResultadoAnalise:
    faltando = politica.ESCOPOS_OBRIGATORIOS - set(dados.escopos)
    if faltando:
        nomes = ", ".join(ROTULOS[e] for e in sorted(faltando))
        raise EscoposObrigatoriosAusentes(f"Consentimento sem escopos obrigatórios: {nomes}")
    modelo = modelo or carregar_modelo()
    fatores = calcular_fatores(dados)
    pontuacao = pontuar(fatores, modelo)
    contrib = {c.chave: c for c in pontuacao.contribuicoes}

    explicados = [
        FatorExplicado(
            **f.model_dump(), pontos=contrib[f.chave].pontos, valor_usado=contrib[f.chave].valor_usado
        )
        for f in fatores
    ]

    calculados = sum(1 for f in fatores if f.status is StatusFator.CALCULADO)
    conf, motivos_confianca = politica.confianca(dados.permanencia.meses_na_base, calculados)
    pelo_score = politica.decisao_pelo_score(pontuacao.score)
    decisao = politica.decidir(pontuacao.score, conf)

    motivos_revisao = list(motivos_confianca)
    if pelo_score is politica.Decisao.REVISAO:
        motivos_revisao.insert(
            0, f"Score na faixa intermediária ({politica.LIMIAR_REVISAO}–{politica.LIMIAR_APROVACAO - 1})"
        )

    ordenados = sorted(explicados, key=lambda f: f.pontos, reverse=True)
    pontos_fortes = [f"{f.rotulo}: {f.evidencia}" for f in ordenados if f.pontos >= 5]
    pontos_de_atencao = [f"{f.rotulo}: {f.evidencia}" for f in reversed(ordenados) if f.pontos <= -5]
    # Fator sem peso no modelo não muda o score; não faz sentido pedir que o titular o autorize.
    nao_autorizados = [
        f.rotulo
        for f in explicados
        if f.status is StatusFator.NAO_AUTORIZADO and modelo.coeficientes[f.chave]
    ]
    if nao_autorizados:
        pontos_de_atencao.append(
            "Sem autorização para: "
            + ", ".join(nao_autorizados)
            + ". Estes fatores entram com o pior valor possível."
        )

    # Plano de melhora: dicas dos fatores que mais tiram pontos primeiro.
    plano = [f.dica for f in sorted(explicados, key=lambda f: f.pontos) if f.dica]
    if nao_autorizados:
        plano.append("Autorizar os dados que ficaram de fora pode aumentar o score")

    oferta = None
    if decisao is not politica.Decisao.RECUSADO:
        oferta = politica.ofertar(pontuacao.score, valor_solicitado)

    return ResultadoAnalise(
        telefone=dados.telefone,
        score=pontuacao.score,
        faixa=politica.faixa(pontuacao.score),
        decisao=decisao,
        decisao_pelo_score=pelo_score,
        confianca=conf,
        probabilidade_inadimplencia=pontuacao.probabilidade_inadimplencia,
        pontos_base=pontuacao.pontos_base,
        fatores=explicados,
        pontos_fortes=pontos_fortes,
        pontos_de_atencao=pontos_de_atencao,
        motivos_revisao=motivos_revisao if decisao is politica.Decisao.REVISAO else [],
        plano_de_melhora=plano,
        oferta=oferta,
        modelo_versao=modelo.versao,
    )
