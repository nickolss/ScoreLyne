"""API do consumidor (porta 8003): cadastro, consentimento, score próprio e explicação."""

# Sem `from __future__ import annotations`: o FastAPI precisa resolver `Logado`, definido em create_app.
import os
from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from scorelyne.comum.auth import Autenticador
from scorelyne.comum.erros import ErroApi
from scorelyne.comum.operadora import Operadora
from scorelyne.operadora.models import Consentimento
from scorelyne.score.formulas import RegistroFormulas, carregar_formulas
from scorelyne.score.modelo import carregar_modelo

from . import servico
from .db import ClienteDB, criar_sessoes
from .esquemas import (
    AtualizarDados,
    Cadastro,
    Cliente,
    Login,
    MeuScore,
    PedidoConsentimento,
    PedidoScore,
    Sessao,
)


def _sessao(request: Request) -> Iterator[Session]:
    with request.app.state.sessoes() as s:
        yield s


Db = Annotated[Session, Depends(_sessao)]


def create_app(
    db_url: str | None = None,
    operadora_url: str | None = None,
    transporte: httpx.BaseTransport | None = None,
    segredo: str | None = None,
) -> FastAPI:
    operadora = Operadora(
        httpx.Client(
            base_url=operadora_url or os.getenv("OPERADORA_URL", "http://localhost:8001"),
            timeout=10,
            transport=transporte,
        )
    )
    auth = Autenticador("consumidor", segredo or os.getenv("CONSUMIDOR_JWT_SECRET"))

    app = FastAPI(
        title="Consumidor — ScoreLyne",
        version="0.1.0",
        description="Cadastro, consentimento e score explicável para o próprio consumidor.",
    )
    app.state.sessoes = criar_sessoes(db_url)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CONSUMIDOR_CORS", "http://localhost:3000").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ErroApi)
    def _erro(_: Request, exc: ErroApi):
        return JSONResponse(status_code=exc.status, content={"detail": exc.mensagem})

    def logado(s: Db, sujeito: Annotated[str, Depends(auth.sujeito)]) -> ClienteDB:
        return servico.obter(s, sujeito)

    Logado = Annotated[ClienteDB, Depends(logado)]

    @app.get("/saude", tags=["infra"])
    def saude():
        return {"status": "ok", "modelo": carregar_modelo().versao}

    @app.get("/formulas", response_model=RegistroFormulas, tags=["transparencia"])
    def formulas():
        """Como o seu score é calculado: fórmulas versionadas, abertas a qualquer pessoa."""
        return carregar_formulas()

    # --- Conta -------------------------------------------------------------------

    @app.post("/cadastro", status_code=201, response_model=Cliente, tags=["conta"])
    def cadastro(dados: Cadastro, s: Db):
        return servico.publico(servico.cadastrar(s, dados))

    @app.post("/login", response_model=Sessao, tags=["conta"])
    def login(dados: Login, s: Db):
        c = servico.autenticar(s, dados)
        return Sessao(token=auth.criar_token(c.id), cliente=servico.publico(c))

    @app.get("/me", response_model=Cliente, tags=["conta"])
    def me(c: Logado):
        return servico.publico(c)

    @app.patch("/meus-dados", response_model=Cliente, tags=["conta"])
    def meus_dados(dados: AtualizarDados, c: Logado, s: Db):
        """Corrige ocupação, cidade, UF ou telefone. Trocar o telefone revoga o consentimento."""
        return servico.publico(servico.atualizar(s, operadora, c, dados))

    # --- Consentimento e score ------------------------------------------------------

    @app.post("/consentimentos", status_code=201, response_model=Consentimento, tags=["score"])
    def consentir(pedido: PedidoConsentimento, c: Logado, s: Db):
        """Autoriza a leitura dos seus dados na operadora, só dos blocos escolhidos."""
        return servico.consentir(s, operadora, c, pedido)

    @app.post("/meu-score", response_model=MeuScore, tags=["score"])
    def calcular(pedido: PedidoScore, c: Logado, s: Db):
        servico.calcular(s, operadora, c, pedido)
        return servico.meu_score(c)

    @app.get("/meu-score", response_model=MeuScore, tags=["score"])
    def ver_score(c: Logado):
        return servico.meu_score(c)

    @app.post("/revogar", response_model=Cliente, tags=["score"])
    def revogar(c: Logado, s: Db):
        """Revoga o consentimento: a operadora bloqueia o acesso e o score guardado é apagado."""
        return servico.publico(servico.revogar(s, operadora, c))

    return app
