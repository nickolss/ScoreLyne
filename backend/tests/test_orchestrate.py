import yaml

from scorelyne.banco import agente
from scorelyne.banco.orchestrate import gerar_agente, gerar_spec


def test_spec_atende_exigencias_do_orchestrate():
    spec = gerar_spec("https://exemplo.test/")

    assert spec["openapi"].startswith("3.0")
    assert spec["servers"] == [{"url": "https://exemplo.test"}]
    ops = [op for caminho in spec["paths"].values() for op in caminho.values()]
    assert sorted(op["operationId"] for op in ops) == sorted(f.nome for f in agente.FERRAMENTAS)
    assert all(op["description"] for op in ops)

    texto = str(spec)
    assert "'null'" not in texto and "anyOf" not in texto and "examples" not in texto
    for nome, schema in spec["components"]["schemas"].items():
        assert "$ref" not in schema or len(schema) == 1, nome


def test_spec_expoe_so_leitura_e_simulacao():
    spec = gerar_spec("http://x")
    assert "/solicitacoes/{solicitacao_id}/decisao" not in spec["paths"]
    assert "/solicitacoes/{solicitacao_id}/revogar" not in spec["paths"]
    assert set(spec["paths"]["/solicitacoes"]) == {"get"}


def test_agente_usa_as_mesmas_instrucoes_e_ferramentas_do_copiloto():
    definicao = yaml.safe_load(gerar_agente("watsonx/ibm/granite-4-h-small"))
    assert definicao["kind"] == "native"
    assert definicao["llm"] == "watsonx/ibm/granite-4-h-small"
    assert definicao["instructions"] == agente.INSTRUCOES
    assert definicao["tools"] == [f.nome for f in agente.FERRAMENTAS]


def test_spec_autentica_o_agente_por_chave_e_nao_por_argumento():
    spec = gerar_spec("http://x")
    assert spec["components"]["securitySchemes"]["agenteKey"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-Agent-Key",
    }
    for caminho in spec["paths"].values():
        for op in caminho.values():
            assert op["security"] == [{"agenteKey": []}]
            assert not any(p["name"].lower().startswith("x-") for p in op.get("parameters", []))
