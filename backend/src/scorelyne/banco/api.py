"""API do credor (porta 8002): fila de solicitações, revisão humana, análise avulsa e cartão do modelo.

Três tipos de credencial, nenhuma anônima (só /saude, /login e /modelo são públicos):
- analista (JWT do /login): decide, desfaz e usa o copiloto;
- agente (cabeçalho X-Agent-Key): só leitura e simulação, para o watsonx Orchestrate via túnel;
- serviço (cabeçalho X-Service-Key): o módulo do consumidor cria e revoga solicitações.
"""

# Sem `from __future__ import annotations`: o FastAPI precisa resolver os tipos definidos em create_app.
import os
from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from scorelyne.comum.auth import Autenticador, bearer, chave_valida
from scorelyne.comum.cartao import CartaoModelo, cartao_modelo
from scorelyne.comum.erros import ErroApi
from scorelyne.comum.operadora import Operadora
from scorelyne.operadora.models import DadosLinha
from scorelyne.score.analise import ResultadoAnalise
from scorelyne.score.formulas import RegistroFormulas, carregar_formulas
from scorelyne.score.modelo import carregar_modelo

from . import agente, copiloto, servico
from .db import AnalistaDB, criar_sessoes
from .esquemas import (
    DecisaoAnalista,
    LoginAnalista,
    NovaSolicitacao,
    SessaoAnalista,
    SituacaoSolicitacao,
    Solicitacao,
    SolicitacaoResumo,
    Status,
)


class PedidoAnalise(BaseModel):
    telefone: str = Field(pattern=r"^\d{10,11}$", examples=["11987124821"])
    consentimento_id: str
    valor_solicitado: Annotated[float | None, Field(gt=0)] = None


class PedidoAnaliseDados(BaseModel):
    dados: DadosLinha
    valor_solicitado: Annotated[float | None, Field(gt=0)] = None


def _sessao(request: Request) -> Iterator[Session]:
    with request.app.state.sessoes() as s:
        yield s


Sessao = Annotated[Session, Depends(_sessao)]


def create_app(
    db_url: str | None = None,
    operadora_url: str | None = None,
    transporte: httpx.BaseTransport | None = None,
    assistente: copiloto.Provedor | None = None,
    segredo: str | None = None,
    chave_servico: str | None = None,
    chave_agente: str | None = None,
) -> FastAPI:
    sessoes = criar_sessoes(db_url)
    auth = Autenticador("analista", segredo or os.getenv("CREDOR_JWT_SECRET"))
    chave_servico = chave_servico or os.getenv("CREDOR_SERVICE_KEY")
    chave_agente = chave_agente or os.getenv("CREDOR_AGENT_KEY")
    operadora = Operadora(
        httpx.Client(
            base_url=operadora_url or os.getenv("OPERADORA_URL", "http://localhost:8001"),
            timeout=10,
            transport=transporte,
        )
    )

    app = FastAPI(
        title="Credor — ScoreLyne",
        version="0.2.0",
        description="Solicitações de crédito com score explicável a partir de dados telecom autorizados.",
    )
    app.state.sessoes = sessoes
    app.state.auth = auth
    assistente = assistente or copiloto.do_ambiente()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("BANCO_CORS", "http://localhost:3000").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ErroApi)
    def _erro(_: Request, exc: ErroApi):
        return JSONResponse(status_code=exc.status, content={"detail": exc.mensagem})

    def analista_logado(s: Sessao, sujeito: Annotated[str, Depends(auth.sujeito)]) -> AnalistaDB:
        return servico.obter_analista(s, sujeito)

    Analista = Annotated[AnalistaDB, Depends(analista_logado)]

    def leitura(
        credencial: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        x_agent_key: Annotated[str | None, Header()] = None,
    ) -> str:
        """Analista logado ou agente do Orchestrate, para as rotas que só leem ou simulam."""
        if chave_valida(x_agent_key, chave_agente):
            return "agente"
        return auth.sujeito(credencial)

    def interno(x_service_key: Annotated[str | None, Header()] = None) -> None:
        if not chave_valida(x_service_key, chave_servico):
            raise ErroApi(403, "Chave de serviço ausente ou inválida")

    Leitura = Depends(leitura)
    Interno = Depends(interno)

    @app.get("/saude", tags=["infra"])
    def saude():
        return {"status": "ok", "modelo": carregar_modelo().versao}

    @app.post("/login", response_model=SessaoAnalista, tags=["analista"])
    def login(dados: LoginAnalista, s: Sessao):
        a = servico.autenticar_analista(s, dados)
        return SessaoAnalista(token=auth.criar_token(a.id), nome=a.nome)

    # --- Solicitações ----------------------------------------------------------

    @app.post(
        "/solicitacoes",
        status_code=201,
        response_model=Solicitacao,
        tags=["solicitacoes"],
        dependencies=[Interno],
    )
    def criar_solicitacao(pedido: NovaSolicitacao, s: Sessao):
        """Busca os dados autorizados na operadora, roda o agente de score e registra o pedido."""
        return servico.completa(servico.criar(s, operadora, pedido))

    @app.get(
        "/solicitacoes", response_model=list[SolicitacaoResumo], tags=["solicitacoes"], dependencies=[Leitura]
    )
    def listar_solicitacoes(s: Sessao, status: Annotated[Status | None, Query()] = None):
        return [servico.resumo(x) for x in servico.listar(s, status)]

    @app.get(
        "/solicitacoes/{solicitacao_id}",
        response_model=Solicitacao,
        tags=["solicitacoes"],
        dependencies=[Leitura],
    )
    def obter_solicitacao(solicitacao_id: str, s: Sessao):
        return servico.completa(servico.obter(s, solicitacao_id))

    @app.get(
        "/solicitacoes/{solicitacao_id}/situacao",
        response_model=SituacaoSolicitacao,
        tags=["solicitacoes"],
        dependencies=[Interno],
    )
    def situacao(solicitacao_id: str, s: Sessao):
        """Visão da solicitação para o próprio consumidor, pedida pelo módulo do consumidor."""
        return servico.situacao(servico.obter(s, solicitacao_id))

    @app.post("/solicitacoes/{solicitacao_id}/decisao", response_model=Solicitacao, tags=["revisao humana"])
    def decidir(solicitacao_id: str, decisao: DecisaoAnalista, a: Analista, s: Sessao):
        """Decisão do analista logado. Vale para a faixa de revisão e para sobrepor o agente."""
        return servico.completa(servico.decidir(s, solicitacao_id, decisao, a.nome))

    @app.delete("/solicitacoes/{solicitacao_id}/decisao", response_model=Solicitacao, tags=["revisao humana"])
    def desfazer(solicitacao_id: str, _: Analista, s: Sessao):
        return servico.completa(servico.desfazer(s, solicitacao_id))

    @app.post(
        "/solicitacoes/{solicitacao_id}/revogar",
        response_model=Solicitacao,
        tags=["solicitacoes"],
        dependencies=[Interno],
    )
    def revogar(solicitacao_id: str, s: Sessao):
        """O módulo do consumidor repassa a revogação: a operadora bloqueia o acesso e a análise é apagada."""
        return servico.completa(servico.revogar(s, operadora, solicitacao_id))

    # --- Análise avulsa (ferramenta do agente) ---------------------------------

    @app.post("/analises", response_model=ResultadoAnalise, tags=["analise"], dependencies=[Leitura])
    def analisar_por_consentimento(pedido: PedidoAnalise):
        """Calcula score, decisão e explicação sem registrar solicitação."""
        dados = operadora.dados(pedido.telefone, pedido.consentimento_id)
        return servico.analisar_com_tratamento(dados, pedido.valor_solicitado)

    @app.post("/analises/dados", response_model=ResultadoAnalise, tags=["analise"], dependencies=[Leitura])
    def analisar_dados(pedido: PedidoAnaliseDados):
        return servico.analisar_com_tratamento(pedido.dados, pedido.valor_solicitado)

    # --- Copiloto do analista (watsonx Orchestrate ou watsonx.ai) -------------

    @app.get("/copiloto", tags=["copiloto"], dependencies=[Depends(analista_logado)])
    def copiloto_status():
        perguntas = [p for _, _, p in agente.PERGUNTAS_INICIAIS]
        if assistente is None:
            return {"disponivel": False, "provedor": None, "modelo": None, "perguntas": perguntas}
        return {
            "disponivel": True,
            "provedor": assistente.nome,
            "modelo": assistente.modelo,
            "perguntas": perguntas,
        }

    @app.post(
        "/copiloto",
        response_model=copiloto.RespostaCopiloto,
        tags=["copiloto"],
        dependencies=[Depends(analista_logado)],
    )
    def conversar(pedido: copiloto.PedidoCopiloto, s: Sessao):
        """Responde ao analista com o agente do watsonx Orchestrate ou um modelo do watsonx.ai."""
        if assistente is None:
            raise ErroApi(
                503, "Copiloto desligado: configure WATSONX_APIKEY e ORCHESTRATE_* ou WATSONX_PROJECT_ID."
            )
        return assistente.responder(pedido, s, operadora)

    @app.get("/modelo", response_model=CartaoModelo, tags=["governanca"])
    def modelo():
        return cartao_modelo()

    @app.get("/formulas", response_model=RegistroFormulas, tags=["governanca"])
    def formulas():
        """Registro versionado das fórmulas de cálculo do score."""
        return carregar_formulas()

    return app
