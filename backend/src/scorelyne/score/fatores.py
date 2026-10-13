"""Cálculo dos cinco fatores do score a partir da resposta da operadora.

Recebe só a `DadosLinha` (o que o banco vê sob consentimento), nunca o registro interno.
Cada fator sai em 0–100 com uma evidência legível e, quando faz sentido, uma dica de melhora.
"""

from __future__ import annotations

import math
from datetime import date
from enum import StrEnum
from statistics import mean, pstdev

from pydantic import BaseModel

from scorelyne.operadora.models import DadosLinha, Escopo, Plano

JANELA_MESES = 24

ROTULOS: dict[Escopo, str] = {
    Escopo.RECARGAS: "Regularidade de recargas",
    Escopo.PERMANENCIA: "Tempo de permanência na base",
    Escopo.PONTUALIDADE: "Pontualidade de pagamento",
    Escopo.ESTABILIDADE: "Estabilidade do número",
    Escopo.CONSISTENCIA: "Consistência do valor gasto",
}

ORDEM = list(ROTULOS)


class StatusFator(StrEnum):
    CALCULADO = "calculado"
    NAO_AUTORIZADO = "nao_autorizado"  # titular não liberou o escopo
    NAO_SE_APLICA = "nao_se_aplica"  # ex.: regularidade de recarga num pós-pago


class Fator(BaseModel):
    chave: Escopo
    rotulo: str
    status: StatusFator
    valor: float | None = None  # 0–100
    evidencia: str
    dica: str | None = None


class HistoricoInsuficiente(ValueError):
    pass


# --- Utilitários --------------------------------------------------------------

Mes = tuple[int, int]


def _mes(d: date) -> Mes:
    return (d.year, d.month)


def _somar(m: Mes, n: int) -> Mes:
    total = m[0] * 12 + m[1] - 1 + n
    return (total // 12, total % 12 + 1)


def _janela(dados: DadosLinha) -> list[Mes]:
    """Meses completos de relacionamento dentro da janela, terminando no mês de referência."""
    fim = _mes(dados.data_referencia)
    inicio = _somar(fim, -(JANELA_MESES - 1))
    primeiro_mes_cheio = _somar(_mes(dados.permanencia.ativada_em), 1)
    inicio = max(inicio, primeiro_mes_cheio)
    meses, m = [], inicio
    while m <= fim:
        meses.append(m)
        m = _somar(m, 1)
    return meses


def _plano_por_mes(dados: DadosLinha, meses: list[Mes]) -> dict[Mes, Plano]:
    p = dados.permanencia
    mudancas = sorted(p.mudancas_plano, key=lambda x: x.data)
    plano = mudancas[0].de if mudancas else p.plano_atual
    resultado, i = {}, 0
    for m in meses:
        while i < len(mudancas) and _mes(mudancas[i].data) <= m:
            plano = mudancas[i].para
            i += 1
        resultado[m] = plano
    return resultado


def _brl(v: float) -> str:
    return f"R$ {v:,.0f}".replace(",", ".")


def _periodo(n: int) -> str:
    return (
        f"nos últimos {n} meses" if n >= JANELA_MESES else f"em {n} {'mês' if n == 1 else 'meses'} de linha"
    )


def _dos_meses(n: int) -> str:
    return f"dos últimos {n} meses" if n >= JANELA_MESES else f"dos {n} meses de linha"


def tempo_label(meses: int) -> str:
    anos, resto = divmod(meses, 12)
    partes = []
    if anos:
        partes.append(f"{anos} {'ano' if anos == 1 else 'anos'}")
    if resto:
        partes.append(f"{resto} {'mês' if resto == 1 else 'meses'}")
    return " e ".join(partes) or "menos de 1 mês"


def _nao_autorizado(chave: Escopo) -> Fator:
    return Fator(
        chave=chave,
        rotulo=ROTULOS[chave],
        status=StatusFator.NAO_AUTORIZADO,
        evidencia="Dado não autorizado pelo titular",
    )


# --- Fatores ------------------------------------------------------------------


def fator_recargas(dados: DadosLinha, meses: list[Mes], planos: dict[Mes, Plano]) -> Fator:
    chave = Escopo.RECARGAS
    if dados.recargas is None:
        return _nao_autorizado(chave)
    meses_pre = [m for m in meses if planos[m] is Plano.PRE_PAGO]
    if not meses_pre:
        return Fator(
            chave=chave,
            rotulo=ROTULOS[chave],
            status=StatusFator.NAO_SE_APLICA,
            evidencia="Plano com fatura no período: regularidade medida pela pontualidade",
        )
    com_recarga = {_mes(d) for d in dados.recargas.datas} & set(meses_pre)
    valor = 100 * len(com_recarga) / len(meses_pre)
    return Fator(
        chave=chave,
        rotulo=ROTULOS[chave],
        status=StatusFator.CALCULADO,
        valor=round(valor, 1),
        evidencia=f"Recarga em {len(com_recarga)} {_dos_meses(len(meses_pre))}",
        dica="Recarregar todo mês, mesmo valores pequenos, pesa mais que o valor" if valor < 90 else None,
    )


def fator_permanencia(dados: DadosLinha) -> Fator:
    p = dados.permanencia
    valor = 100 * min(1.0, math.log1p(p.meses_na_base) / math.log1p(120))
    evidencia = f"{tempo_label(p.meses_na_base)} na mesma operadora"
    if p.veio_por_portabilidade:
        evidencia += " (chegou por portabilidade)"
    return Fator(
        chave=Escopo.PERMANENCIA,
        rotulo=ROTULOS[Escopo.PERMANENCIA],
        status=StatusFator.CALCULADO,
        valor=round(valor, 1),
        evidencia=evidencia,
        dica="Este fator cresce naturalmente com o tempo de relacionamento" if valor < 60 else None,
    )


def _nota_fatura(atraso: int | None) -> float:
    if atraso is None:  # em aberto
        return 0.0
    if atraso <= 0:
        return 1.0
    if atraso <= 5:
        return 0.7
    if atraso <= 15:
        return 0.4
    if atraso <= 30:
        return 0.15
    return 0.0


def fator_pontualidade(dados: DadosLinha, meses: list[Mes], planos: dict[Mes, Plano]) -> Fator:
    chave = Escopo.PONTUALIDADE
    if dados.pontualidade is None:
        return _nao_autorizado(chave)
    pt = dados.pontualidade
    janela = set(meses)

    faturas = [f for f in pt.faturas if _mes(f.vencimento) in janela]
    atrasos = [(f.pago_em - f.vencimento).days if f.pago_em else None for f in faturas]
    notas = [_nota_fatura(a) for a in atrasos]

    meses_pre = [m for m in meses if planos[m] is Plano.PRE_PAGO]
    zerados: dict[Mes, int] = {}
    for s in pt.saldos_zerados:
        m = _mes(s.data)
        if m in janela:
            zerados[m] = max(zerados.get(m, 0), s.dias_sem_saldo)
    for m in meses_pre:
        dias = zerados.get(m)
        notas.append(1.0 if dias is None else 0.6 if dias <= 7 else 0.2)

    suspensoes = [s for s in pt.suspensoes if _mes(s.inicio) in janela]
    if not notas:
        valor = 50.0
    else:
        valor = max(0.0, min(100.0, 100 * mean(notas) - 10 * len(suspensoes)))

    partes = []
    if faturas:
        em_dia = sum(1 for a in atrasos if a is not None and a <= 0)
        partes.append(f"{em_dia} de {len(faturas)} faturas pagas até o vencimento")
        ultimas = atrasos[-12:]
        graves = sum(1 for a in ultimas if a is None or a > 15)
        if graves:
            partes.append(f"atrasos acima de 15 dias em {graves} das últimas {len(ultimas)}")
    if meses_pre:
        n_zerados = sum(1 for m in meses_pre if m in zerados)
        if n_zerados:
            partes.append(f"ficou sem saldo em {n_zerados} {_dos_meses(len(meses_pre))}")
        else:
            partes.append(f"nunca ficou sem saldo {_periodo(len(meses_pre))}")
    if suspensoes:
        partes.append(
            f"linha suspensa {len(suspensoes)} {'vez' if len(suspensoes) == 1 else 'vezes'} por atraso"
        )
    evidencia = "; ".join(partes) or "Sem faturas ou recargas no período"
    evidencia = evidencia[0].upper() + evidencia[1:]

    dica = None
    if valor < 85:
        if meses_pre and not faturas:
            dica = "Migrar para o plano Controle cria histórico de fatura paga em dia"
        elif faturas:
            dica = "Pagar a fatura até o vencimento é o que mais pesa neste fator"
        else:
            dica = "Recarregar antes do saldo zerar mostra organização financeira"
    return Fator(
        chave=chave,
        rotulo=ROTULOS[chave],
        status=StatusFator.CALCULADO,
        valor=round(valor, 1),
        evidencia=evidencia,
        dica=dica,
    )


def fator_estabilidade(dados: DadosLinha, meses: list[Mes]) -> Fator:
    chave = Escopo.ESTABILIDADE
    if dados.estabilidade is None:
        return _nao_autorizado(chave)
    e = dados.estabilidade
    janela = set(meses)
    trocas = sorted(d for d in e.trocas_chip if _mes(d) in janela)
    portou_recente = (
        e.portabilidade_entrada is not None and (dados.data_referencia - e.portabilidade_entrada).days <= 365
    )
    valor = max(0.0, 100 - 30 * len(trocas) - (20 if portou_recente else 0))

    partes = []
    if trocas:
        datas = ", ".join(d.strftime("%m/%Y") for d in trocas)
        partes.append(f"{len(trocas)} {'troca' if len(trocas) == 1 else 'trocas'} de chip ({datas})")
    if portou_recente:
        partes.append("portabilidade de entrada há menos de 1 ano")
    evidencia = "; ".join(partes) or f"Mesmo número e chip {_periodo(len(meses))}"
    evidencia = evidencia[0].upper() + evidencia[1:]
    return Fator(
        chave=chave,
        rotulo=ROTULOS[chave],
        status=StatusFator.CALCULADO,
        valor=valor,
        evidencia=evidencia,
        dica="Manter o mesmo chip e número reforça este fator" if valor < 70 else None,
    )


def fator_consistencia(dados: DadosLinha, meses: list[Mes]) -> Fator:
    chave = Escopo.CONSISTENCIA
    if dados.consistencia is None:
        return _nao_autorizado(chave)
    janela = {f"{a:04d}-{m:02d}" for a, m in meses}
    gastos = [
        v.total_recargas + (v.valor_fatura or 0)
        for v in dados.consistencia.valores_mensais
        if v.competencia in janela and v.total_recargas + (v.valor_fatura or 0) > 0
    ]
    if len(gastos) < 2:
        return Fator(
            chave=chave,
            rotulo=ROTULOS[chave],
            status=StatusFator.CALCULADO,
            valor=50.0,
            evidencia="Poucos meses com gasto para medir a variação",
        )
    media = mean(gastos)
    cv = pstdev(gastos) / media
    valor = 100 * max(0.0, 1 - cv / 0.8)
    return Fator(
        chave=chave,
        rotulo=ROTULOS[chave],
        status=StatusFator.CALCULADO,
        valor=round(valor, 1),
        evidencia=f"Gasto mensal entre {_brl(min(gastos))} e {_brl(max(gastos))} (média de {_brl(media)})",
        dica="Manter um valor de recarga parecido todo mês aumenta este fator" if valor < 70 else None,
    )


def calcular_fatores(dados: DadosLinha) -> list[Fator]:
    if dados.permanencia is None:
        raise HistoricoInsuficiente("O escopo 'permanencia' é obrigatório para calcular o score")
    meses = _janela(dados)
    if not meses:
        raise HistoricoInsuficiente("A linha ainda não completou um mês de relacionamento")
    planos = _plano_por_mes(dados, meses)
    return [
        fator_recargas(dados, meses, planos),
        fator_permanencia(dados),
        fator_pontualidade(dados, meses, planos),
        fator_estabilidade(dados, meses),
        fator_consistencia(dados, meses),
    ]
