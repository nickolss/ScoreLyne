"""Política de crédito: transforma score em decisão e oferta.

Regras de supervisão humana:
- score na faixa intermediária sempre vai para um analista;
- com baixa confiança (histórico curto ou poucos fatores), o agente não aprova nem recusa sozinho.

Os limiares de probabilidade de inadimplência ligados a 750 e 550 ficam em `modelo.Escala`.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from scorelyne.operadora.models import Escopo

LIMIAR_APROVACAO = 750
LIMIAR_REVISAO = 550
MESES_MINIMOS = 6
FATORES_MINIMOS = 3
LIMITE_MAXIMO = 4000
PRAZOS = (6, 12, 18)

# Fatores de maior peso são obrigatórios. Se fossem opcionais, quem tem histórico ruim
# ganharia pontos só por não autorizar (seleção adversa). Os opcionais, quando faltam,
# entram com o pior valor observado na base (ver `treino.py`): omitir nunca aumenta o score.
ESCOPOS_OBRIGATORIOS = frozenset({Escopo.PERMANENCIA, Escopo.RECARGAS, Escopo.PONTUALIDADE})


class Decisao(StrEnum):
    APROVADO = "aprovado"
    REVISAO = "revisao"
    RECUSADO = "recusado"


class Confianca(StrEnum):
    ALTA = "alta"
    BAIXA = "baixa"


class Parcela(BaseModel):
    prazo_meses: int
    valor_parcela: float
    total: float


class Oferta(BaseModel):
    limite: float
    valor_ofertado: float
    taxa_mensal: float  # em %
    parcelas: list[Parcela]


def faixa(score: int) -> str:
    if score >= 850:
        return "Excelente"
    if score >= LIMIAR_APROVACAO:
        return "Bom"
    if score >= LIMIAR_REVISAO:
        return "Regular"
    return "Em construção"


def decisao_pelo_score(score: int) -> Decisao:
    if score >= LIMIAR_APROVACAO:
        return Decisao.APROVADO
    if score >= LIMIAR_REVISAO:
        return Decisao.REVISAO
    return Decisao.RECUSADO


def confianca(meses_na_base: int, fatores_calculados: int) -> tuple[Confianca, list[str]]:
    motivos = []
    if meses_na_base < MESES_MINIMOS:
        motivos.append(f"Histórico curto: {meses_na_base} meses de relacionamento (mínimo {MESES_MINIMOS})")
    if fatores_calculados < FATORES_MINIMOS:
        motivos.append(f"Só {fatores_calculados} fatores com dado disponível (mínimo {FATORES_MINIMOS})")
    return (Confianca.BAIXA if motivos else Confianca.ALTA), motivos


def decidir(score: int, conf: Confianca) -> Decisao:
    if conf is Confianca.BAIXA:
        return Decisao.REVISAO
    return decisao_pelo_score(score)


def limite_sugerido(score: int) -> float:
    if score < LIMIAR_REVISAO:
        return 0
    return min(LIMITE_MAXIMO, round((score - 500) / 500 * LIMITE_MAXIMO / 100) * 100)


def taxa_mensal(score: int) -> float:
    return round(max(1.9, 5.5 - (score - LIMIAR_REVISAO) * 0.009), 2)


def parcela(principal: float, taxa_pct: float, meses: int) -> float:
    r = taxa_pct / 100
    return principal * r / (1 - (1 + r) ** -meses)


def ofertar(score: int, valor_solicitado: float | None) -> Oferta | None:
    limite = limite_sugerido(score)
    if limite <= 0:
        return None
    valor = min(limite, valor_solicitado) if valor_solicitado else limite
    taxa = taxa_mensal(score)
    parcelas = []
    for prazo in PRAZOS:
        p = parcela(valor, taxa, prazo)
        parcelas.append(Parcela(prazo_meses=prazo, valor_parcela=round(p, 2), total=round(p * prazo, 2)))
    return Oferta(limite=limite, valor_ofertado=valor, taxa_mensal=taxa, parcelas=parcelas)
