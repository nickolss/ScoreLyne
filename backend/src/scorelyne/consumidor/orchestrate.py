"""Gera o agente do consumidor para importar no watsonx Orchestrate.

Diferente do agente do analista, este não tem ferramentas. Um agente do Orchestrate é único e
compartilhado: ele não sabe quem está logado, então ferramentas por HTTP teriam de confiar num
identificador vindo do modelo. Em vez disso, o servidor injeta na conversa só a análise do próprio
cliente (veja `assistente.contexto_do_cliente`), e o agente nunca tem como chegar aos dados de outra
pessoa. As ferramentas por function calling ficam no caminho do watsonx.ai, onde o servidor as executa
sobre o cliente do token.
"""

from __future__ import annotations

import yaml

from . import agente


class _Dumper(yaml.SafeDumper):
    """Textos de várias linhas saem como bloco literal (|), legíveis no YAML."""


_Dumper.add_representer(
    str,
    lambda d, v: d.represent_scalar("tag:yaml.org,2002:str", v, style="|" if "\n" in v else None),
)


def gerar_agente(llm: str) -> str:
    definicao = {
        "spec_version": "v1",
        "kind": "native",
        "name": agente.NOME,
        "display_name": agente.NOME_EXIBICAO,
        "description": agente.DESCRICAO,
        "llm": llm,
        "style": "react_core",
        "instructions": agente.INSTRUCOES
        + "\nVocê não tem ferramentas. Os dados da pessoa chegam no início da conversa, numa mensagem "
        "de sistema; use só eles e, se estiverem ausentes, peça que ela calcule o score primeiro.\n",
        "tools": [],
        "welcome_content": {
            "welcome_message": "Olá! Sou o assistente de score do ScoreLyne. Posso explicar a sua nota.",
            "description": "Não decido crédito: a decisão é sempre do credor.",
        },
        "starter_prompts": {
            "prompts": [
                {"id": f"inicial_{i}", "title": t, "subtitle": sub, "prompt": p, "state": "active"}
                for i, (t, sub, p) in enumerate(agente.PERGUNTAS_INICIAIS, 1)
            ]
        },
    }
    cabecalho = "# Gerado por `uv run consumidor orchestrate` a partir de backend/src/scorelyne/consumidor/agente.py.\n"
    return cabecalho + yaml.dump(definicao, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=110)
