"""Modelos de dados da operadora mock.

`Linha` é o registro interno completo. A API nunca devolve uma `Linha` inteira:
ela monta uma `DadosLinha` só com os blocos cobertos pelo consentimento.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Plano(StrEnum):
    PRE_PAGO = "pre_pago"
    CONTROLE = "controle"
    POS_PAGO = "pos_pago"


class Escopo(StrEnum):
    """Escopos de consentimento. Um para cada fator do score, como na tela do cliente."""

    RECARGAS = "recargas"
    PERMANENCIA = "permanencia"
    PONTUALIDADE = "pontualidade"
    ESTABILIDADE = "estabilidade"
    CONSISTENCIA = "consistencia"


# --- Registro interno ---------------------------------------------------------


class Recarga(BaseModel):
    data: date
    valor: float


class Fatura(BaseModel):
    competencia: str  # "AAAA-MM"
    vencimento: date
    pago_em: date | None  # None = em aberto na data de referência
    valor: float


class SaldoZerado(BaseModel):
    data: date
    dias_sem_saldo: int


class Suspensao(BaseModel):
    inicio: date
    fim: date | None  # None = ainda suspensa


class MudancaPlano(BaseModel):
    data: date
    de: Plano
    para: Plano


class Linha(BaseModel):
    telefone: str
    titular: str
    cpf: str
    cidade: str
    uf: str
    plano: Plano
    ativada_em: date
    portabilidade_entrada: date | None = None
    recargas: list[Recarga] = []
    faturas: list[Fatura] = []
    saldos_zerados: list[SaldoZerado] = []
    suspensoes: list[Suspensao] = []
    trocas_chip: list[date] = []
    mudancas_plano: list[MudancaPlano] = []


class PerfilOculto(BaseModel):
    """Verdade de base usada para gerar a linha. Nunca sai pela API; só no export de treino."""

    disciplina: float
    volatilidade: float
    mobilidade: float
    inadimplente: bool


# --- Consentimento ------------------------------------------------------------


class ConsentimentoEntrada(BaseModel):
    telefone: str = Field(pattern=r"^\d{10,11}$", examples=["11987124821"])
    cpf: str = Field(pattern=r"^\d{11}$", description="CPF do titular, conferido com o cadastro da linha")
    escopos: list[Escopo] = Field(min_length=1)
    finalidade: str = Field(min_length=3, examples=["analise_de_credito"])
    solicitante: str = Field(min_length=2, examples=["Banco Parceiro S.A."])
    validade_dias: int = Field(default=30, ge=1, le=90)


class Acesso(BaseModel):
    em: datetime
    escopos: list[Escopo]


class Consentimento(BaseModel):
    id: str
    telefone: str
    escopos: list[Escopo]
    finalidade: str
    solicitante: str
    criado_em: datetime
    expira_em: datetime
    revogado_em: datetime | None = None
    acessos: list[Acesso] = []


# --- Resposta de dados (um bloco por escopo) ----------------------------------


class DadosPermanencia(BaseModel):
    ativada_em: date
    meses_na_base: int
    plano_atual: Plano
    veio_por_portabilidade: bool
    mudancas_plano: list[MudancaPlano]


class DadosRecargas(BaseModel):
    datas: list[date] = Field(description="Só as datas. Valores ficam no escopo de consistência.")


class FaturaPagamento(BaseModel):
    competencia: str
    vencimento: date
    pago_em: date | None


class DadosPontualidade(BaseModel):
    faturas: list[FaturaPagamento]
    saldos_zerados: list[SaldoZerado]
    suspensoes: list[Suspensao]


class DadosEstabilidade(BaseModel):
    trocas_chip: list[date]
    portabilidade_entrada: date | None


class ValorMensal(BaseModel):
    competencia: str
    total_recargas: float
    valor_fatura: float | None


class DadosConsistencia(BaseModel):
    valores_mensais: list[ValorMensal] = Field(
        description="Totais agregados por mês, sem transações individuais."
    )


class DadosLinha(BaseModel):
    telefone: str
    consentimento_id: str
    data_referencia: date
    escopos: list[Escopo]
    permanencia: DadosPermanencia | None = None
    recargas: DadosRecargas | None = None
    pontualidade: DadosPontualidade | None = None
    estabilidade: DadosEstabilidade | None = None
    consistencia: DadosConsistencia | None = None
