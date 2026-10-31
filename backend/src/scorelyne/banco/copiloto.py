"""Copiloto do analista no painel do credor.

Dois provedores, escolhidos pelo ambiente (backend/.env):

1. watsonx Orchestrate (preferido): o painel conversa com o agente importado por
   `uv run banco orchestrate`. O agente chama as ferramentas na API do credor pelo túnel público,
   autenticado com a chave de agente (CREDOR_AGENT_KEY).
       ORCHESTRATE_URL       https://api.<regiao>.watson-orchestrate.cloud.ibm.com/instances/<id>
       ORCHESTRATE_AGENT_ID  id do agente (`orchestrate agents list`)

2. watsonx.ai: um modelo de chat recebe as instruções e as ferramentas de `agente.py`, que rodam
   aqui mesmo, sobre o serviço do credor, até o modelo responder em texto.
       WATSONX_URL           https://us-south.ml.cloud.ibm.com
       WATSONX_PROJECT_ID    projeto do watsonx.ai (ou WATSONX_SPACE_ID)
       WATSONX_MODEL         ibm/granite-4-h-small

Os dois autenticam com a mesma chave de API do IBM Cloud em WATSONX_APIKEY. Os clientes do IBM em
si ficam em `scorelyne.comum.ibm`, compartilhados com o assistente do consumidor.
"""

from __future__ import annotations

import os
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from scorelyne.comum import ibm
from scorelyne.comum.cartao import cartao_modelo
from scorelyne.comum.erros import ErroApi
from scorelyne.comum.ibm import (  # noqa: F401  (reexportados: a API e os testes importam daqui)
    ChamadaFerramenta,
    ConfigOrchestrate,
    ConfigWatsonx,
    TokenIAM,
)
from scorelyne.comum.operadora import Operadora

from . import agente, servico
from .esquemas import Status


class Mensagem(BaseModel):
    papel: Literal["analista", "copiloto"]
    texto: str = Field(min_length=1, max_length=4000)


class PedidoCopiloto(BaseModel):
    mensagens: list[Mensagem] = Field(min_length=1, max_length=30)


class RespostaCopiloto(BaseModel):
    resposta: str
    ferramentas: list[ChamadaFerramenta]  # vazia no Orchestrate, que roda as ferramentas por conta própria
    provedor: str
    modelo: str


class Provedor(Protocol):
    nome: str
    modelo: str

    def responder(
        self, pedido: PedidoCopiloto, sessao: Session, operadora: Operadora
    ) -> RespostaCopiloto: ...


def _historico(pedido: PedidoCopiloto) -> list[dict]:
    return [
        {"role": "user" if m.papel == "analista" else "assistant", "content": m.texto}
        for m in pedido.mensagens
    ]


class Orchestrate:
    """Conversa com o agente do analista no watsonx Orchestrate."""

    nome = ibm.Orchestrate.nome

    def __init__(self, config: ConfigOrchestrate, transporte: httpx.BaseTransport | None = None):
        self.modelo = agente.NOME
        self._cliente = ibm.Orchestrate(config, self.modelo, transporte)

    def responder(self, pedido: PedidoCopiloto, sessao: Session, operadora: Operadora) -> RespostaCopiloto:
        texto, modelo = self._cliente.conversar(_historico(pedido))
        return RespostaCopiloto(resposta=texto, ferramentas=[], provedor=self.nome, modelo=modelo)


class Watsonx:
    """Chat do watsonx.ai; as ferramentas do analista rodam aqui, sobre o serviço do credor."""

    nome = ibm.Watsonx.nome

    def __init__(self, config: ConfigWatsonx, transporte: httpx.BaseTransport | None = None):
        self.modelo = config.modelo
        self._cliente = ibm.Watsonx(config, transporte)

    def responder(self, pedido: PedidoCopiloto, sessao: Session, operadora: Operadora) -> RespostaCopiloto:
        texto, chamadas = ibm.conversar_com_ferramentas(
            self._cliente,
            agente.INSTRUCOES,
            _historico(pedido),
            FERRAMENTAS_CHAT,
            lambda nome, args: executar(nome, args, sessao, operadora),
        )
        return RespostaCopiloto(resposta=texto, ferramentas=chamadas, provedor=self.nome, modelo=self.modelo)


def do_ambiente() -> Provedor | None:
    """Orchestrate se estiver configurado; senão watsonx.ai; senão o copiloto fica desligado."""
    if not os.getenv("WATSONX_APIKEY"):
        return None
    if config := ibm.config_orchestrate_do_ambiente("ORCHESTRATE_AGENT_ID"):
        return Orchestrate(config)
    if config := ibm.config_watsonx_do_ambiente():
        return Watsonx(config)
    return None


FERRAMENTAS_CHAT = ibm.ferramentas_para_chat(agente.FERRAMENTAS)


def executar(nome: str, args: dict[str, Any], sessao: Session, operadora: Operadora) -> Any:
    """Roda uma ferramenta do agente diretamente sobre o serviço do credor."""
    if nome == "listar_solicitacoes":
        status = Status(args["status"]) if args.get("status") else None
        return [servico.resumo(s).model_dump(mode="json") for s in servico.listar(sessao, status)]
    if nome == "obter_solicitacao":
        s = servico.completa(servico.obter(sessao, str(args["solicitacao_id"])))
        return s.model_dump(mode="json")
    if nome == "simular_analise":
        dados = operadora.dados(str(args["telefone"]), str(args["consentimento_id"]))
        valor = args.get("valor_solicitado")
        return servico.analisar_com_tratamento(dados, float(valor) if valor else None).model_dump(mode="json")
    if nome == "obter_cartao_modelo":
        return cartao_modelo().model_dump(mode="json")
    raise ErroApi(400, f"Ferramenta desconhecida: {nome}")
