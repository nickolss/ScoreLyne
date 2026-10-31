"""Clientes do IBM Cloud usados pelos assistentes do credor e do consumidor.

- `TokenIAM`: troca a chave de API (WATSONX_APIKEY) por um token de acesso.
- `Orchestrate`: conversa com um agente do watsonx Orchestrate (API de chat compatível com a da OpenAI).
- `Watsonx`: chat do watsonx.ai com function calling; as ferramentas rodam aqui, no processo.
- `conversar_com_ferramentas`: o laço "modelo pede ferramenta -> executa -> devolve" até haver texto.

Cada serviço fornece só as instruções, a lista de ferramentas e a função que as executa.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel

from .erros import ErroApi

IAM_URL = "https://iam.cloud.ibm.com/identity/token"
VERSAO_API = "2024-10-08"
MAX_RODADAS = 6


class ChamadaFerramenta(BaseModel):
    nome: str
    argumentos: dict[str, Any]
    erro: str | None = None


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
                raise ErroApi(502, "Não foi possível autenticar no IBM Cloud. Confira WATSONX_APIKEY.")
            corpo = r.json()
            self._token = corpo["access_token"]
            self._expira = float(corpo.get("expiration", time.time() + 3600))
        return {"Authorization": f"Bearer {self._token}"}


@dataclass(frozen=True)
class ConfigOrchestrate:
    url: str
    apikey: str
    agente_id: str


class Orchestrate:
    """Cliente do agente do watsonx Orchestrate."""

    nome = "watsonx Orchestrate"

    def __init__(self, config: ConfigOrchestrate, modelo: str, transporte: httpx.BaseTransport | None = None):
        self.config = config
        self.modelo = modelo
        self.http = httpx.Client(timeout=120, transport=transporte)
        self.iam = TokenIAM(config.apikey, self.http)

    def conversar(self, historico: list[dict]) -> tuple[str, str]:
        """Devolve (texto da resposta, modelo informado pelo Orchestrate)."""
        r = self.http.post(
            f"{self.config.url}/v1/orchestrate/{self.config.agente_id}/chat/completions",
            headers=self.iam.cabecalho(),
            json={"messages": historico, "stream": False},
        )
        if r.status_code != 200:
            raise ErroApi(502, f"watsonx Orchestrate respondeu {r.status_code}: {r.text[:300]}")
        corpo = r.json()
        texto = (corpo["choices"][0]["message"].get("content") or "").strip()
        return texto, corpo.get("model") or self.modelo


@dataclass(frozen=True)
class ConfigWatsonx:
    url: str
    apikey: str
    projeto: str | None
    espaco: str | None
    modelo: str


class Watsonx:
    """Chat mínimo do watsonx.ai com function calling."""

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
            raise ErroApi(502, f"watsonx.ai respondeu {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]


def config_watsonx_do_ambiente() -> ConfigWatsonx | None:
    apikey = os.getenv("WATSONX_APIKEY")
    projeto, espaco = os.getenv("WATSONX_PROJECT_ID"), os.getenv("WATSONX_SPACE_ID")
    if not apikey or not (projeto or espaco):
        return None
    return ConfigWatsonx(
        url=os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/"),
        apikey=apikey,
        projeto=projeto,
        espaco=espaco,
        modelo=os.getenv("WATSONX_MODEL", "ibm/granite-4-h-small"),
    )


def config_orchestrate_do_ambiente(variavel_agente: str) -> ConfigOrchestrate | None:
    """`variavel_agente` diz qual agente: ORCHESTRATE_AGENT_ID (analista) ou o do consumidor."""
    apikey, url, agente_id = (
        os.getenv("WATSONX_APIKEY"),
        os.getenv("ORCHESTRATE_URL"),
        os.getenv(variavel_agente),
    )
    if not (apikey and url and agente_id):
        return None
    return ConfigOrchestrate(url.rstrip("/"), apikey, agente_id)


def ferramentas_para_chat(ferramentas) -> list[dict]:
    """Converte a lista de ferramentas (nome, descricao, parametros) para o formato do watsonx.ai."""
    return [
        {
            "type": "function",
            "function": {"name": f.nome, "description": f.descricao, "parameters": f.parametros},
        }
        for f in ferramentas
    ]


def conversar_com_ferramentas(
    watsonx: Watsonx,
    instrucoes: str,
    historico: list[dict],
    ferramentas: list[dict],
    executar: Callable[[str, dict[str, Any]], Any],
) -> tuple[str, list[ChamadaFerramenta]]:
    """Roda o laço de ferramentas. Devolve (resposta, chamadas feitas).

    `executar` só recebe o nome e os argumentos que o modelo escolheu; qualquer identidade (quem está
    perguntando) tem de vir de fora, do login, e nunca dos argumentos.
    """
    mensagens: list[dict] = [{"role": "system", "content": instrucoes}, *historico]
    chamadas: list[ChamadaFerramenta] = []

    for _ in range(MAX_RODADAS):
        msg = watsonx.chat(mensagens, ferramentas)
        pedidas = msg.get("tool_calls") or []
        if not pedidas:
            return (msg.get("content") or "").strip(), chamadas

        mensagens.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": pedidas})
        for pedida in pedidas:
            nome = pedida["function"]["name"]
            chamada = ChamadaFerramenta(nome=nome, argumentos={})
            try:
                chamada.argumentos = json.loads(pedida["function"].get("arguments") or "{}")
                resultado = executar(nome, chamada.argumentos)
            except (ErroApi, KeyError, ValueError, TypeError) as exc:
                chamada.erro = exc.mensagem if isinstance(exc, ErroApi) else f"Argumentos inválidos: {exc}"
                resultado = {"erro": chamada.erro}
            chamadas.append(chamada)
            mensagens.append(
                {
                    "role": "tool",
                    "tool_call_id": pedida["id"],
                    "content": json.dumps(resultado, ensure_ascii=False),
                }
            )

    return (
        "Não consegui concluir a resposta com as consultas disponíveis. Tente reformular a pergunta.",
        chamadas,
    )
