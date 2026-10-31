"""Assistente do consumidor: explica o score da própria pessoa com IA da IBM.

Dois provedores, escolhidos pelo ambiente (backend/.env):

1. watsonx.ai (ferramentas locais): o modelo recebe as instruções e as ferramentas de `agente.py`.
   Elas rodam aqui, sobre os dados do cliente logado, que o servidor fixa a partir do token.
       WATSONX_PROJECT_ID (ou WATSONX_SPACE_ID), WATSONX_MODEL

2. watsonx Orchestrate: um agente sem ferramentas. Como o agente do Orchestrate é compartilhado e não
   sabe quem está logado, o servidor injeta na conversa só a análise do próprio cliente. Assim o
   agente nunca tem acesso a dados de outra pessoa, nem por prompt injection.
       ORCHESTRATE_URL, ORCHESTRATE_CONSUMIDOR_AGENT_ID

Os dois autenticam com WATSONX_APIKEY. Os clientes do IBM ficam em `scorelyne.comum.ibm`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field

from scorelyne.comum import ibm
from scorelyne.comum.analise import analisar_com_tratamento
from scorelyne.comum.erros import ErroApi
from scorelyne.comum.ibm import ChamadaFerramenta, ConfigOrchestrate, ConfigWatsonx
from scorelyne.comum.operadora import Operadora
from scorelyne.score.fatores import ROTULOS
from scorelyne.score.formulas import carregar_formulas

from . import agente
from .db import ClienteDB


class MensagemAssistente(BaseModel):
    papel: Literal["cliente", "assistente"]
    texto: str = Field(min_length=1, max_length=4000)


class PedidoAssistente(BaseModel):
    mensagens: list[MensagemAssistente] = Field(min_length=1, max_length=30)


class RespostaAssistente(BaseModel):
    resposta: str
    ferramentas: list[ChamadaFerramenta]  # vazia no Orchestrate, que não usa ferramentas aqui
    provedor: str
    modelo: str


class Assistente(Protocol):
    nome: str
    modelo: str

    def responder(
        self, pedido: PedidoAssistente, cliente: ClienteDB, operadora: Operadora
    ) -> RespostaAssistente: ...


def _historico(pedido: PedidoAssistente) -> list[dict]:
    return [
        {"role": "user" if m.papel == "cliente" else "assistant", "content": m.texto}
        for m in pedido.mensagens
    ]


def _sem_telefone(analise: dict) -> dict:
    """O modelo não precisa do telefone para explicar o score, então ele nem chega lá."""
    return {k: v for k, v in analise.items() if k != "telefone"}


def _analise_do_cliente(cliente: ClienteDB) -> dict:
    if not cliente.analise:
        raise ErroApi(404, "A pessoa ainda não calculou o score: peça que autorize os dados e calcule antes")
    return _sem_telefone(cliente.analise)


def executar(nome: str, args: dict[str, Any], cliente: ClienteDB, operadora: Operadora) -> Any:
    """Roda uma ferramenta sobre o cliente logado. `args` vem do modelo e nunca escolhe o cliente."""
    if nome == "meu_score":
        return _analise_do_cliente(cliente)
    if nome == "explicar_fator":
        chave = str(args["fator"])
        if chave not in {e.value for e in ROTULOS}:
            raise ErroApi(400, f"Fator desconhecido: {chave}")
        fator = next(f for f in _analise_do_cliente(cliente)["fatores"] if f["chave"] == chave)
        formula = next(f for f in carregar_formulas().fatores if f.id.value == chave)
        return {"fator": fator, "formula": formula.model_dump(mode="json")}
    if nome == "simular_alteracao":
        if not cliente.consentimento_id:
            raise ErroApi(409, "A pessoa não tem consentimento ativo: não há dados para simular")
        dados = operadora.dados(cliente.telefone, cliente.consentimento_id)
        resultado = analisar_com_tratamento(dados, float(args["valor_solicitado"]))
        return {"simulacao": True, **_sem_telefone(resultado.model_dump(mode="json"))}
    if nome == "como_e_calculado":
        return carregar_formulas().model_dump(mode="json")
    raise ErroApi(400, f"Ferramenta desconhecida: {nome}")


FERRAMENTAS_CHAT = ibm.ferramentas_para_chat(agente.FERRAMENTAS)


class AssistenteWatsonx:
    """Chat do watsonx.ai com as ferramentas do consumidor rodando aqui."""

    nome = ibm.Watsonx.nome

    def __init__(self, config: ConfigWatsonx, transporte: httpx.BaseTransport | None = None):
        self.modelo = config.modelo
        self._cliente = ibm.Watsonx(config, transporte)

    def responder(
        self, pedido: PedidoAssistente, cliente: ClienteDB, operadora: Operadora
    ) -> RespostaAssistente:
        texto, chamadas = ibm.conversar_com_ferramentas(
            self._cliente,
            agente.INSTRUCOES,
            _historico(pedido),
            FERRAMENTAS_CHAT,
            lambda nome, args: executar(nome, args, cliente, operadora),
        )
        return RespostaAssistente(
            resposta=texto, ferramentas=chamadas, provedor=self.nome, modelo=self.modelo
        )


def contexto_do_cliente(cliente: ClienteDB) -> str:
    """Mensagem de sistema com os dados do próprio cliente, para o agente do Orchestrate."""
    if cliente.analise:
        dados = {
            "analise": _sem_telefone(cliente.analise),
            "valor_solicitado": cliente.valor_solicitado,
            "finalidade": cliente.finalidade,
            "formulas": [
                {"fator": f.id.value, "formula": f.formula, "observacao": f.observacao}
                for f in carregar_formulas().fatores
            ],
        }
        corpo = json.dumps(dados, ensure_ascii=False)
    else:
        corpo = "O cliente ainda não calculou o score."
    return (
        "Dados do cliente que está conversando agora (confidenciais, só dele). Use apenas isto para "
        "responder; não há outra fonte e você não tem como consultar outras pessoas.\n" + corpo
    )


class AssistenteOrchestrate:
    """Agente do Orchestrate sem ferramentas, alimentado só com os dados do cliente logado."""

    nome = ibm.Orchestrate.nome

    def __init__(self, config: ConfigOrchestrate, transporte: httpx.BaseTransport | None = None):
        self.modelo = agente.NOME
        self._cliente = ibm.Orchestrate(config, self.modelo, transporte)

    def responder(
        self, pedido: PedidoAssistente, cliente: ClienteDB, operadora: Operadora
    ) -> RespostaAssistente:
        historico = [{"role": "system", "content": contexto_do_cliente(cliente)}, *_historico(pedido)]
        texto, modelo = self._cliente.conversar(historico)
        return RespostaAssistente(resposta=texto, ferramentas=[], provedor=self.nome, modelo=modelo)


def do_ambiente() -> Assistente | None:
    """Orchestrate se o agente do consumidor estiver configurado; senão watsonx.ai; senão desligado."""
    if not os.getenv("WATSONX_APIKEY"):
        return None
    if config := ibm.config_orchestrate_do_ambiente("ORCHESTRATE_CONSUMIDOR_AGENT_ID"):
        return AssistenteOrchestrate(config)
    if config := ibm.config_watsonx_do_ambiente():
        return AssistenteWatsonx(config)
    return None
