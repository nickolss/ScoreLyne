"""Contratos da API do consumidor."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from scorelyne.operadora.generator import cpf_valido
from scorelyne.operadora.models import Escopo
from scorelyne.score.analise import ResultadoAnalise


class Cadastro(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    cpf: str = Field(pattern=r"^\d{11}$")
    telefone: str = Field(pattern=r"^\d{10,11}$")
    senha: str = Field(min_length=8, max_length=72)
    ocupacao: str | None = Field(default=None, max_length=120)
    cidade: str | None = Field(default=None, max_length=80)
    uf: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str) -> str:
        if not cpf_valido(v):
            raise ValueError("CPF inválido")
        return v


class Login(BaseModel):
    cpf: str = Field(pattern=r"^\d{11}$")
    senha: str


class AtualizarDados(BaseModel):
    """Campos que o consumidor pode corrigir. Trocar o telefone exige um novo consentimento."""

    telefone: str | None = Field(default=None, pattern=r"^\d{10,11}$")
    ocupacao: str | None = Field(default=None, max_length=120)
    cidade: str | None = Field(default=None, max_length=80)
    uf: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")


class Cliente(BaseModel):
    id: str
    nome: str
    cpf: str
    telefone: str
    ocupacao: str | None
    cidade: str | None
    uf: str | None
    consentimento_ativo: bool
    escopos: list[Escopo]
    enviado_ao_credor: bool


class Sessao(BaseModel):
    token: str
    tipo: str = "bearer"
    cliente: Cliente


class PedidoConsentimento(BaseModel):
    escopos: list[Escopo] = Field(min_length=1)
    validade_dias: int = Field(default=30, ge=1, le=90)


class PedidoScore(BaseModel):
    valor_solicitado: Annotated[float, Field(gt=0, le=50_000)]
    finalidade: str = Field(min_length=2, max_length=200)


class MeuScore(BaseModel):
    valor_solicitado: float
    finalidade: str
    calculado_em: datetime
    escopos: list[Escopo]
    analise: ResultadoAnalise
