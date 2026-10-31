"""Exporta as ferramentas do agente para o watsonx Orchestrate.

O Orchestrate importa ferramentas a partir de um spec OpenAPI com algumas exigências: versão 3.0,
um único servidor sem parâmetros, `operationId` em snake_case (vira o nome da ferramenta) e
descrição em cada operação (o agente usa para escolher a ferramenta). O FastAPI gera 3.1, então
este módulo filtra as operações expostas ao agente e converte o que muda entre as versões.
Também gera o YAML do agente a partir de `agente.py`.
"""

from __future__ import annotations

import copy
from typing import Any

import yaml

from . import agente
from .api import create_app


def _para_30(no: Any) -> Any:
    """Converte um schema JSON Schema 2020-12 (OpenAPI 3.1) para o dialeto do OpenAPI 3.0."""
    if isinstance(no, list):
        return [_para_30(x) for x in no]
    if not isinstance(no, dict):
        return no

    s = {k: v for k, v in no.items() if k != "properties"}
    if "properties" in no:
        s["properties"] = {nome: _para_30(sub) for nome, sub in no["properties"].items()}
    for chave in ("items", "additionalProperties", "allOf", "oneOf", "anyOf", "not"):
        if isinstance(s.get(chave), (dict, list)):
            s[chave] = _para_30(s[chave])

    # anyOf: [X, {type: null}]  ->  X com nullable
    if "anyOf" in s:
        sem_nulo = [x for x in s["anyOf"] if x.get("type") != "null"]
        if len(sem_nulo) < len(s["anyOf"]):
            del s["anyOf"]
            s["nullable"] = True
            if len(sem_nulo) == 1:
                unico = sem_nulo[0]
                # $ref não aceita irmãos no 3.0, então vai dentro de um allOf
                s.update({"allOf": [unico]} if "$ref" in unico else unico)
            else:
                s["anyOf"] = sem_nulo

    if isinstance(s.get("type"), list):
        tipos = [t for t in s["type"] if t != "null"]
        s["nullable"] = len(tipos) < len(s["type"]) or s.get("nullable", False)
        s["type"] = tipos[0]
    if "const" in s:
        s["enum"] = [s.pop("const")]
    if isinstance(s.get("examples"), list):
        exemplos = s.pop("examples")
        if exemplos:
            s["example"] = exemplos[0]
    for limite, base in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
        if isinstance(s.get(limite), (int, float)) and not isinstance(s[limite], bool):
            s[base] = s.pop(limite)
            s[limite] = True
    return s


def _schemas_em(no: Any) -> Any:
    """Aplica `_para_30` em todo `schema` dentro de operações, parâmetros e respostas."""
    if isinstance(no, list):
        return [_schemas_em(x) for x in no]
    if not isinstance(no, dict):
        return no
    return {k: _para_30(v) if k == "schema" else _schemas_em(v) for k, v in no.items()}


def _refs(no: Any, achados: set[str]) -> None:
    if isinstance(no, dict):
        ref = no.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            achados.add(ref.rsplit("/", 1)[1])
        for v in no.values():
            _refs(v, achados)
    elif isinstance(no, list):
        for v in no:
            _refs(v, achados)


def gerar_spec(url_servidor: str) -> dict[str, Any]:
    """Spec OpenAPI 3.0 só com as ferramentas do agente, apontando para `url_servidor`."""
    original = create_app(db_url="sqlite://").openapi()

    caminhos: dict[str, dict] = {}
    for f in agente.FERRAMENTAS:
        op = copy.deepcopy(original["paths"][f.caminho][f.metodo])
        op["operationId"] = f.nome
        op["description"] = f.descricao
        op["responses"] = {c: r for c, r in op["responses"].items() if c != "422"}
        # A autenticação é uma conexão do Orchestrate (chave de API), não um argumento da ferramenta.
        op["parameters"] = [p for p in op.get("parameters", []) if not p["name"].lower().startswith("x-")]
        if not op["parameters"]:
            del op["parameters"]
        op["security"] = [{"agenteKey": []}]
        caminhos.setdefault(f.caminho, {})[f.metodo] = op

    # Mantém só os schemas alcançáveis a partir das operações escolhidas
    todos = original["components"]["schemas"]
    usados: set[str] = set()
    _refs(caminhos, usados)
    pendentes = list(usados)
    while pendentes:
        novos: set[str] = set()
        _refs(todos[pendentes.pop()], novos)
        for nome in novos - usados:
            usados.add(nome)
            pendentes.append(nome)

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "ScoreLyne — ferramentas do analista de crédito",
            "version": original["info"]["version"],
            "description": original["info"].get("description", ""),
        },
        "servers": [{"url": url_servidor.rstrip("/")}],
        "paths": _schemas_em(caminhos),
        "components": {
            "schemas": {nome: _para_30(todos[nome]) for nome in sorted(usados)},
            "securitySchemes": {"agenteKey": {"type": "apiKey", "in": "header", "name": "X-Agent-Key"}},
        },
    }


class _Dumper(yaml.SafeDumper):
    """Textos de várias linhas saem como bloco literal (|), legíveis no YAML."""


_Dumper.add_representer(
    str,
    lambda d, v: d.represent_scalar("tag:yaml.org,2002:str", v, style="|" if "\n" in v else None),
)


def gerar_agente(llm: str) -> str:
    """YAML do agente nativo do Orchestrate, com as mesmas instruções do copiloto do painel."""
    definicao = {
        "spec_version": "v1",
        "kind": "native",
        "name": agente.NOME,
        "display_name": agente.NOME_EXIBICAO,
        "description": agente.DESCRICAO,
        "llm": llm,
        "style": "react_core",
        "instructions": agente.INSTRUCOES,
        "guidelines": [
            {
                "condition": "O analista pergunta quais casos precisam de atenção ou o que há na fila",
                "action": "Liste as solicitações com status revisao, do mais antigo para o mais novo",
                "tool": "listar_solicitacoes",
            },
            {
                "condition": "O analista pergunta se o modelo é justo, confiável ou como ele funciona",
                "action": "Consulte o cartão do modelo e explique métricas e equidade em linguagem simples",
                "tool": "obter_cartao_modelo",
            },
        ],
        "tools": [f.nome for f in agente.FERRAMENTAS],
        "welcome_content": {
            "welcome_message": (
                "Olá! Sou o copiloto de crédito do ScoreLyne. "
                "Posso explicar scores, revisar a fila e simular ofertas."
            ),
            "description": "A decisão final é sempre sua.",
        },
        "starter_prompts": {
            "prompts": [
                {"id": f"inicial_{i}", "title": t, "subtitle": sub, "prompt": p, "state": "active"}
                for i, (t, sub, p) in enumerate(agente.PERGUNTAS_INICIAIS, 1)
            ]
        },
    }
    cabecalho = "# Gerado por `uv run banco orchestrate` a partir de backend/src/scorelyne/banco/agente.py.\n"
    return cabecalho + yaml.dump(definicao, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=110)
