"""API REST da operadora mock.

Simula o lado da operadora na parceria: o banco só recebe dados de uma linha
mediante um consentimento válido do titular, e só os blocos que ele autorizou.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .generator import DATA_REFERENCIA
from .models import Consentimento, ConsentimentoEntrada, DadosLinha, Plano
from .store import Base, ErroConsentimento


class LinhaDemo(BaseModel):
    chave: str | None
    telefone: str
    titular: str
    cpf: str
    plano: Plano
    cidade: str
    uf: str


def create_app(
    tamanho_populacao: int | None = None, semente: int | None = None, demo: bool | None = None
) -> FastAPI:
    tamanho_populacao = tamanho_populacao or int(os.getenv("OPERADORA_POPULACAO", "3000"))
    semente = semente if semente is not None else int(os.getenv("OPERADORA_SEMENTE", "42"))
    demo = demo if demo is not None else os.getenv("OPERADORA_DEMO", "1") == "1"

    base = Base(tamanho_populacao, semente)
    app = FastAPI(
        title="Operadora Mock — ScoreLyne",
        version="0.1.0",
        description=(
            "Dados sintéticos de uma operadora de telefonia. Toda leitura de dados de uma linha exige "
            "um consentimento ativo do titular, enviado no cabeçalho `X-Consentimento-Id`."
        ),
    )
    app.state.base = base
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("OPERADORA_CORS", "http://localhost:3000").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ErroConsentimento)
    def _erro_consentimento(_: Request, exc: ErroConsentimento):
        return JSONResponse(status_code=exc.status, content={"detail": exc.mensagem})

    @app.get("/saude", tags=["infra"])
    def saude():
        return {"status": "ok", "linhas": len(base.linhas), "data_referencia": DATA_REFERENCIA}

    @app.post("/consentimentos", status_code=201, response_model=Consentimento, tags=["consentimento"])
    def criar_consentimento(entrada: ConsentimentoEntrada):
        """Registra o consentimento do titular. Na vida real, a operadora confirmaria por SMS."""
        return base.criar_consentimento(entrada)

    @app.get("/consentimentos/{consentimento_id}", response_model=Consentimento, tags=["consentimento"])
    def obter_consentimento(consentimento_id: str):
        """Consentimento com a trilha de cada acesso feito aos dados."""
        return base.obter_consentimento(consentimento_id)

    @app.delete("/consentimentos/{consentimento_id}", response_model=Consentimento, tags=["consentimento"])
    def revogar_consentimento(consentimento_id: str):
        return base.revogar_consentimento(consentimento_id)

    @app.get(
        "/linhas/{telefone}/dados",
        response_model=DadosLinha,
        response_model_exclude_unset=True,
        tags=["dados"],
        responses={401: {"description": "Sem consentimento"}, 403: {"description": "Consentimento inválido"}},
    )
    def dados_linha(
        telefone: str,
        x_consentimento_id: Annotated[str | None, Header()] = None,
    ):
        """Devolve só os blocos cobertos pelo consentimento. Cada chamada fica registrada."""
        if not x_consentimento_id:
            raise HTTPException(401, "Envie o cabeçalho X-Consentimento-Id")
        return base.dados(telefone, x_consentimento_id)

    if demo:

        @app.get("/demo/personas", response_model=list[LinhaDemo], tags=["demo"])
        def personas():
            """Telefones e CPFs das personas da demo. Desligue com OPERADORA_DEMO=0."""
            return [_linha_demo(chave, linha) for chave, linha in base.personas.items()]

        @app.get("/demo/linhas", response_model=list[LinhaDemo], tags=["demo"])
        def linhas(
            offset: Annotated[int, Query(ge=0)] = 0,
            limite: Annotated[int, Query(ge=1, le=200)] = 20,
        ):
            """Amostra da população sintética para testes."""
            telefones = list(base.perfis)[offset : offset + limite]
            return [_linha_demo(None, base.linhas[t]) for t in telefones]

    return app


def _linha_demo(chave: str | None, linha) -> LinhaDemo:
    return LinhaDemo(
        chave=chave,
        telefone=linha.telefone,
        titular=linha.titular,
        cpf=linha.cpf,
        plano=linha.plano,
        cidade=linha.cidade,
        uf=linha.uf,
    )
