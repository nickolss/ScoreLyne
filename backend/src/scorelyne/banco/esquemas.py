"""Contratos da API do banco."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from scorelyne.comum.contratos import RevisaoHumana, SituacaoSolicitacao, Status, Veredito
from scorelyne.score.analise import ResultadoAnalise
from scorelyne.score.politica import Decisao


class NovaSolicitacao(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    telefone: str = Field(pattern=r"^\d{10,11}$")
    consentimento_id: str
    valor_solicitado: Annotated[float, Field(gt=0, le=50_000)]
    finalidade: str = Field(min_length=2, max_length=200)
    ocupacao: str | None = None
    cidade: str | None = None
    uf: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")


__all__ = ["RevisaoHumana", "SituacaoSolicitacao", "Status", "Veredito"]


class LoginAnalista(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    senha: str


class SessaoAnalista(BaseModel):
    token: str
    tipo: str = "bearer"
    nome: str


class AnalistaPerfil(BaseModel):
    nome: str
    email: str


class DecisaoAnalista(BaseModel):
    """Veredito e justificativa. Quem decidiu vem do login, nunca do corpo da requisição."""

    veredito: Veredito
    justificativa: str = Field(min_length=10, max_length=2000)


class Evento(BaseModel):
    em: datetime
    ator: str
    tipo: str
    titulo: str
    detalhe: str | None


class SolicitacaoResumo(BaseModel):
    id: str
    criado_em: datetime
    nome: str
    ocupacao: str | None
    plano: str | None
    valor_solicitado: float
    score: int | None
    decisao_agente: Decisao
    status: Status


class Solicitacao(SolicitacaoResumo):
    atualizado_em: datetime
    telefone: str
    cidade: str | None
    uf: str | None
    finalidade: str
    consentimento_id: str
    escopos: list[str]
    analise: ResultadoAnalise | None
    revisao_humana: RevisaoHumana | None
    revogado_em: datetime | None
    eventos: list[Evento]
