"""Contratos trocados entre o módulo do consumidor e o do credor.

Ficam em `comum` para nenhum dos dois pacotes importar o outro: o que cruza a fronteira entre os
serviços é só isto.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from scorelyne.score.politica import Decisao, Oferta


class Status(StrEnum):
    APROVADO = "aprovado"
    REVISAO = "revisao"
    RECUSADO = "recusado"
    REVOGADO = "revogado"


class Veredito(StrEnum):
    APROVAR = "aprovar"
    RECUSAR = "recusar"


class RevisaoHumana(BaseModel):
    veredito: Veredito
    justificativa: str
    analista: str
    em: datetime


class SituacaoSolicitacao(BaseModel):
    """O que o consumidor pode saber da própria solicitação: sem trilha interna nem dados de terceiros."""

    id: str
    status: Status
    decisao_agente: Decisao
    score: int | None
    oferta: Oferta | None
    motivos_revisao: list[str]
    revisao_humana: RevisaoHumana | None
    atualizado_em: datetime


class TrocaDeSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=72)
    nova_senha: str = Field(min_length=8, max_length=72)
