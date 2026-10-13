"""Copiloto do analista no painel do banco.

Dois provedores, escolhidos pelo ambiente (backend/.env):

1. watsonx Orchestrate (preferido): o painel conversa com o agente importado por
   `uv run banco orchestrate`. O agente chama as ferramentas na API do banco pelo túnel público.
       ORCHESTRATE_URL       https://api.<regiao>.watson-orchestrate.cloud.ibm.com/instances/<id>
       ORCHESTRATE_AGENT_ID  id do agente (`orchestrate agents list`)

2. watsonx.ai: um modelo de chat recebe as instruções e as ferramentas de `agente.py`, que rodam
   aqui mesmo, sobre o serviço do banco, até o modelo responder em texto.
       WATSONX_URL           https://us-south.ml.cloud.ibm.com
       WATSONX_PROJECT_ID    projeto do watsonx.ai (ou WATSONX_SPACE_ID)
       WATSONX_MODEL         ibm/granite-4-h-small

Os dois autenticam com a mesma chave de API do IBM Cloud em WATSONX_APIKEY.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import agente, servico
from .esquemas import Status
from .servico import ErroBanco, Operadora

IAM_URL = "https://iam.cloud.ibm.com/identity/token"
VERSAO_API = "2024-10-08"
MAX_RODADAS = 6


class Mensagem(BaseModel):
    papel: Literal["analista", "copiloto"]
    texto: str = Field(min_length=1, max_length=4000)


class PedidoCopiloto(BaseModel):
    mensagens: list[Mensagem] = Field(min_length=1, max_length=30)


class ChamadaFerramenta(BaseModel):
    nome: str
    argumentos: dict[str, Any]
    erro: str | None = None


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


class TokenIAM:
    """Troca a chave de API do IBM Cloud por um token de acesso e o guarda até perto de expirar."""

    def __init__(self, apikey: str, http: httpx.Client):
        self.apikey = apikey
        self.http = http
        self._token: str | None = None
        self._expira = 0.0

    def cabecalho(self) -> dict[str, str]:
        if not self._token or time.time() > self._expira - 60:
            r = self.http.post(
                IAM_URL, data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": self.apikey}
            )
            if r.status_code != 200:
                raise ErroBanco(502, "Não foi possível autenticar no IBM Cloud. Confira WATSONX_APIKEY.")
            corpo = r.json()
            self._token = corpo["access_token"]
            self._expira = float(corpo.get("expiration", time.time() + 3600))
        return {"Authorization": f"Bearer {self._token}"}


def _historico(pedido: PedidoCopiloto) -> list[dict]:
    return [
        {"role": "user" if m.papel == "analista" else "assistant", "content": m.texto}
        for m in pedido.mensagens
    ]


@dataclass(frozen=True)
class ConfigOrchestrate:
    url: str
    apikey: str
    agente_id: str


class Orchestrate:
    """Conversa com o agente do watsonx Orchestrate pela API de chat compatível com a da OpenAI."""

    nome = "watsonx Orchestrate"

    def __init__(self, config: ConfigOrchestrate, transporte: httpx.BaseTransport | None = None):
        self.config = config
        self.http = httpx.Client(timeout=120, transport=transporte)
        self.iam = TokenIAM(config.apikey, self.http)
        self.modelo = agente.NOME

    def responder(self, pedido: PedidoCopiloto, sessao: Session, operadora: Operadora) -> RespostaCopiloto:
        r = self.http.post(
            f"{self.config.url}/v1/orchestrate/{self.config.agente_id}/chat/completions",
            headers=self.iam.cabecalho(),
            json={"messages": _historico(pedido), "stream": False},
        )
        if r.status_code != 200:
            raise ErroBanco(502, f"watsonx Orchestrate respondeu {r.status_code}: {r.text[:300]}")
        corpo = r.json()
        return RespostaCopiloto(
            resposta=(corpo["choices"][0]["message"].get("content") or "").strip(),
            ferramentas=[],
            provedor=self.nome,
            modelo=corpo.get("model") or self.modelo,
        )


@dataclass(frozen=True)
class ConfigWatsonx:
    url: str
    apikey: str
    projeto: str | None
    espaco: str | None
    modelo: str


class Watsonx:
    """Cliente mínimo do chat do watsonx.ai; as ferramentas rodam aqui, sobre o serviço do banco."""

    nome = "watsonx.ai"

    def __init__(self, config: ConfigWatsonx, transporte: httpx.BaseTransport | None = None):
        self.config = config
        self.http = httpx.Client(timeout=60, transport=transporte)
        self.iam = TokenIAM(config.apikey, self.http)
        self.modelo = config.modelo

    def chat(self, mensagens: list[dict], ferramentas: list[dict]) -> dict:
        corpo: dict[str, Any] = {
            "model_id": self.config.modelo,
            "messages": mensagens,
            "tools": ferramentas,
            "tool_choice_option": "auto",
            "max_tokens": 1500,
            "temperature": 0,
        }
        if self.config.projeto:
            corpo["project_id"] = self.config.projeto
        else:
            corpo["space_id"] = self.config.espaco
        r = self.http.post(
            f"{self.config.url}/ml/v1/text/chat",
            params={"version": VERSAO_API},
            headers=self.iam.cabecalho(),
            json=corpo,
        )
        if r.status_code != 200:
            raise ErroBanco(502, f"watsonx.ai respondeu {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]

    def responder(self, pedido: PedidoCopiloto, sessao: Session, operadora: Operadora) -> RespostaCopiloto:
        return responder(pedido, self, sessao, operadora)


def do_ambiente() -> Provedor | None:
    """Orchestrate se estiver configurado; senão watsonx.ai; senão o copiloto fica desligado."""
    apikey = os.getenv("WATSONX_APIKEY")
    if not apikey:
        return None
    url, agente_id = os.getenv("ORCHESTRATE_URL"), os.getenv("ORCHESTRATE_AGENT_ID")
    if url and agente_id:
        return Orchestrate(ConfigOrchestrate(url.rstrip("/"), apikey, agente_id))
    projeto, espaco = os.getenv("WATSONX_PROJECT_ID"), os.getenv("WATSONX_SPACE_ID")
    if projeto or espaco:
        return Watsonx(
            ConfigWatsonx(
                url=os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/"),
                apikey=apikey,
                projeto=projeto,
                espaco=espaco,
                modelo=os.getenv("WATSONX_MODEL", "ibm/granite-4-h-small"),
            )
        )
    return None


FERRAMENTAS_CHAT = [
    {"type": "function", "function": {"name": f.nome, "description": f.descricao, "parameters": f.parametros}}
    for f in agente.FERRAMENTAS
]


def executar(nome: str, args: dict[str, Any], sessao: Session, operadora: Operadora) -> Any:
    """Roda uma ferramenta do agente diretamente sobre o serviço do banco."""
    from .api import cartao_modelo

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
    raise ErroBanco(400, f"Ferramenta desconhecida: {nome}")


def responder(
    pedido: PedidoCopiloto, watsonx: Watsonx, sessao: Session, operadora: Operadora
) -> RespostaCopiloto:
    mensagens: list[dict] = [{"role": "system", "content": agente.INSTRUCOES}, *_historico(pedido)]
    chamadas: list[ChamadaFerramenta] = []

    for _ in range(MAX_RODADAS):
        msg = watsonx.chat(mensagens, FERRAMENTAS_CHAT)
        pedidas = msg.get("tool_calls") or []
        if not pedidas:
            return RespostaCopiloto(
                resposta=(msg.get("content") or "").strip(),
                ferramentas=chamadas,
                provedor=watsonx.nome,
                modelo=watsonx.modelo,
            )

        mensagens.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": pedidas})
        for pedida in pedidas:
            nome = pedida["function"]["name"]
            chamada = ChamadaFerramenta(nome=nome, argumentos={})
            try:
                chamada.argumentos = json.loads(pedida["function"].get("arguments") or "{}")
                resultado = executar(nome, chamada.argumentos, sessao, operadora)
            except (ErroBanco, KeyError, ValueError, TypeError) as exc:
                chamada.erro = exc.mensagem if isinstance(exc, ErroBanco) else f"Argumentos inválidos: {exc}"
                resultado = {"erro": chamada.erro}
            chamadas.append(chamada)
            mensagens.append(
                {
                    "role": "tool",
                    "tool_call_id": pedida["id"],
                    "content": json.dumps(resultado, ensure_ascii=False),
                }
            )

    return RespostaCopiloto(
        resposta="Não consegui concluir a resposta com as consultas disponíveis. Tente reformular a pergunta.",
        ferramentas=chamadas,
        provedor=watsonx.nome,
        modelo=watsonx.modelo,
    )
