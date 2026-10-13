"""API do banco (porta 8002): solicitações, revisão humana, análise avulsa e cartão do modelo."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from scorelyne.operadora.models import DadosLinha, Escopo
from scorelyne.score import politica
from scorelyne.score.analise import ResultadoAnalise
from scorelyne.score.fatores import ROTULOS
from scorelyne.score.modelo import Escala, carregar_modelo

from . import agente, copiloto, servico
from .db import criar_sessoes
from .esquemas import DecisaoAnalista, NovaSolicitacao, Solicitacao, SolicitacaoResumo, Status
from .servico import ErroBanco, Operadora


class PedidoAnalise(BaseModel):
    telefone: str = Field(pattern=r"^\d{10,11}$", examples=["11987124821"])
    consentimento_id: str
    valor_solicitado: Annotated[float | None, Field(gt=0)] = None


class PedidoAnaliseDados(BaseModel):
    dados: DadosLinha
    valor_solicitado: Annotated[float | None, Field(gt=0)] = None


class FatorModelo(BaseModel):
    chave: Escopo
    rotulo: str
    importancia: float
    obrigatorio: bool
    ativo: bool
    perda_maxima_se_omitir: int  # pontos que o score pode cair se o titular não autorizar


class CartaoModelo(BaseModel):
    """Resumo público do modelo, para a página de governança e para auditoria."""

    versao: str
    fatores: list[FatorModelo]
    limiares: dict[str, int]
    escala: Escala
    metricas: dict[str, float]
    equidade: dict


def cartao_modelo() -> CartaoModelo:
    m = carregar_modelo()
    return CartaoModelo(
        versao=m.versao,
        fatores=[
            FatorModelo(
                chave=k,
                rotulo=ROTULOS[k],
                importancia=m.importancia[k],
                obrigatorio=k in politica.ESCOPOS_OBRIGATORIOS,
                ativo=m.coeficientes[k] != 0,
                perda_maxima_se_omitir=round(
                    m.escala.fator * abs(m.coeficientes[k]) * (100 - m.conservador[k]) / 100
                ),
            )
            for k in ROTULOS
        ],
        limiares={"aprovacao": politica.LIMIAR_APROVACAO, "revisao": politica.LIMIAR_REVISAO},
        escala=m.escala,
        metricas=m.metricas,
        equidade=m.equidade,
    )


def _sessao(request: Request) -> Iterator[Session]:
    with request.app.state.sessoes() as s:
        yield s


Sessao = Annotated[Session, Depends(_sessao)]


def create_app(
    db_url: str | None = None,
    operadora_url: str | None = None,
    transporte: httpx.BaseTransport | None = None,
    assistente: copiloto.Provedor | None = None,
) -> FastAPI:
    sessoes = criar_sessoes(db_url)
    operadora = Operadora(
        httpx.Client(
            base_url=operadora_url or os.getenv("OPERADORA_URL", "http://localhost:8001"),
            timeout=10,
            transport=transporte,
        )
    )

    app = FastAPI(
        title="Banco — ScoreLyne",
        version="0.2.0",
        description="Solicitações de crédito com score explicável a partir de dados telecom autorizados.",
    )
    app.state.sessoes = sessoes
    assistente = assistente or copiloto.do_ambiente()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("BANCO_CORS", "http://localhost:3000").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ErroBanco)
    def _erro(_: Request, exc: ErroBanco):
        return JSONResponse(status_code=exc.status, content={"detail": exc.mensagem})

    @app.get("/saude", tags=["infra"])
    def saude():
        return {"status": "ok", "modelo": carregar_modelo().versao}

    # --- Solicitações ----------------------------------------------------------

    @app.post("/solicitacoes", status_code=201, response_model=Solicitacao, tags=["solicitacoes"])
    def criar_solicitacao(pedido: NovaSolicitacao, s: Sessao):
        """Busca os dados autorizados na operadora, roda o agente de score e registra o pedido."""
        return servico.completa(servico.criar(s, operadora, pedido))

    @app.get("/solicitacoes", response_model=list[SolicitacaoResumo], tags=["solicitacoes"])
    def listar_solicitacoes(s: Sessao, status: Annotated[Status | None, Query()] = None):
        return [servico.resumo(x) for x in servico.listar(s, status)]

    @app.get("/solicitacoes/{solicitacao_id}", response_model=Solicitacao, tags=["solicitacoes"])
    def obter_solicitacao(solicitacao_id: str, s: Sessao):
        return servico.completa(servico.obter(s, solicitacao_id))

    @app.post("/solicitacoes/{solicitacao_id}/decisao", response_model=Solicitacao, tags=["revisao humana"])
    def decidir(solicitacao_id: str, decisao: DecisaoAnalista, s: Sessao):
        """Decisão do analista. Vale para a faixa de revisão e para sobrepor o agente."""
        return servico.completa(servico.decidir(s, solicitacao_id, decisao))

    @app.delete("/solicitacoes/{solicitacao_id}/decisao", response_model=Solicitacao, tags=["revisao humana"])
    def desfazer(solicitacao_id: str, s: Sessao):
        return servico.completa(servico.desfazer(s, solicitacao_id))

    @app.post("/solicitacoes/{solicitacao_id}/revogar", response_model=Solicitacao, tags=["solicitacoes"])
    def revogar(solicitacao_id: str, s: Sessao):
        """O cliente revoga o consentimento: a operadora bloqueia o acesso e a análise é apagada."""
        return servico.completa(servico.revogar(s, operadora, solicitacao_id))

    # --- Análise avulsa (ferramenta do agente) ---------------------------------

    @app.post("/analises", response_model=ResultadoAnalise, tags=["analise"])
    def analisar_por_consentimento(pedido: PedidoAnalise):
        """Calcula score, decisão e explicação sem registrar solicitação."""
        dados = operadora.dados(pedido.telefone, pedido.consentimento_id)
        return servico.analisar_com_tratamento(dados, pedido.valor_solicitado)

    @app.post("/analises/dados", response_model=ResultadoAnalise, tags=["analise"])
    def analisar_dados(pedido: PedidoAnaliseDados):
        return servico.analisar_com_tratamento(pedido.dados, pedido.valor_solicitado)

    # --- Copiloto do analista (watsonx Orchestrate ou watsonx.ai) -------------

    @app.get("/copiloto", tags=["copiloto"])
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

    @app.post("/copiloto", response_model=copiloto.RespostaCopiloto, tags=["copiloto"])
    def conversar(pedido: copiloto.PedidoCopiloto, s: Sessao):
        """Responde ao analista com o agente do watsonx Orchestrate ou um modelo do watsonx.ai."""
        if assistente is None:
            raise ErroBanco(
                503, "Copiloto desligado: configure WATSONX_APIKEY e ORCHESTRATE_* ou WATSONX_PROJECT_ID."
            )
        return assistente.responder(pedido, s, operadora)

    @app.get("/modelo", response_model=CartaoModelo, tags=["governanca"])
    def modelo():
        return cartao_modelo()

    return app
