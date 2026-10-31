"""Assistente do consumidor: o modelo só enxerga e consulta os dados de quem está logado."""

import json

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from scorelyne.comum.ibm import ConfigOrchestrate, ConfigWatsonx
from scorelyne.consumidor import agente
from scorelyne.consumidor.api import create_app as criar_consumidor
from scorelyne.consumidor.assistente import AssistenteOrchestrate, AssistenteWatsonx
from scorelyne.consumidor.orchestrate import gerar_agente
from scorelyne.operadora.api import create_app as criar_operadora
from tests.test_consumidor import TODOS, _cadastrar, _entrar, _Ponte

PERGUNTA = {"mensagens": [{"papel": "cliente", "texto": "Por que minha nota ficou assim?"}]}


class _WatsonxFalso(httpx.BaseTransport):
    """Simula o IAM e o chat do watsonx.ai: pede as ferramentas combinadas e depois responde em texto."""

    def __init__(self, chamadas: list[tuple[str, dict]]):
        self.chamadas = chamadas
        self.corpos: list[dict] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "iam.cloud.ibm.com":
            return httpx.Response(200, json={"access_token": "t", "expiration": 9e9})
        self.corpos.append(json.loads(request.content))
        if len(self.corpos) == 1:
            pedidas = [
                {"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
                for i, (n, a) in enumerate(self.chamadas)
            ]
            mensagem = {"role": "assistant", "content": "", "tool_calls": pedidas}
        else:
            mensagem = {"role": "assistant", "content": "Sua nota vem principalmente da pontualidade."}
        return httpx.Response(200, json={"choices": [{"message": mensagem}]})

    def resultados(self) -> list[dict]:
        """Conteúdo das mensagens de ferramenta que o modelo recebeu na segunda chamada."""
        return [json.loads(m["content"]) for m in self.corpos[1]["messages"] if m["role"] == "tool"]


def _montar(ia_factory=None):
    operadora = TestClient(criar_operadora(tamanho_populacao=50, semente=1, demo=True))
    ia = ia_factory() if ia_factory else None
    app = criar_consumidor(
        db_url="sqlite://",
        operadora_url="http://operadora",
        transporte=_Ponte(operadora),
        segredo="segredo-de-teste-com-32-bytes-ou-mais!!",
        ia=ia,
    )
    return operadora, TestClient(app), ia


def _com_score(operadora, consumidor, chave):
    p = _cadastrar(operadora, consumidor, chave)
    h = _entrar(consumidor, p["cpf"])
    consumidor.post("/consentimentos", json={"escopos": TODOS}, headers=h).raise_for_status()
    consumidor.post(
        "/meu-score", json={"valor_solicitado": 1000, "finalidade": "Teste"}, headers=h
    ).raise_for_status()
    return p, h


def _watsonx(chamadas):
    falso = _WatsonxFalso(chamadas)
    config = ConfigWatsonx("http://wx", "k", "proj", None, "ibm/granite-4-h-small")
    return falso, lambda: AssistenteWatsonx(config, falso)


def test_meu_score_devolve_a_analise_de_quem_esta_logado_sem_o_telefone():
    falso, fabrica = _watsonx([("meu_score", {})])
    operadora, consumidor, _ = _montar(fabrica)
    p, h = _com_score(operadora, consumidor, "maria")

    r = consumidor.post("/assistente", json=PERGUNTA, headers=h)

    assert r.status_code == 200, r.text
    assert r.json()["resposta"] == "Sua nota vem principalmente da pontualidade."
    assert [c["nome"] for c in r.json()["ferramentas"]] == ["meu_score"]
    (analise,) = falso.resultados()
    esperado = consumidor.get("/meu-score", headers=h).json()["analise"]
    assert analise["score"] == esperado["score"]
    assert "telefone" not in analise
    assert p["telefone"] not in json.dumps(falso.corpos)  # nem nas mensagens enviadas ao modelo


def test_modelo_nao_escolhe_o_cliente_nem_com_argumento_malicioso():
    """Mesmo pedindo o cliente de outra pessoa, a ferramenta usa quem está logado."""
    falso, fabrica = _watsonx([("meu_score", {"cliente_id": "outra-pessoa", "cpf": "00000000000"})])
    operadora, consumidor, _ = _montar(fabrica)
    _com_score(operadora, consumidor, "maria")  # a análise que João não pode receber
    joao = _cadastrar(operadora, consumidor, "joao")
    h_joao = _entrar(consumidor, joao["cpf"])  # João ainda não calculou o score

    r = consumidor.post("/assistente", json=PERGUNTA, headers=h_joao)

    assert r.status_code == 200
    (resultado,) = falso.resultados()
    assert "erro" in resultado, "João não pode receber a análise da Maria"
    assert "score" not in resultado
    assert r.json()["ferramentas"][0]["erro"] == resultado["erro"]


def test_explicar_fator_traz_a_formula_do_registro_e_rejeita_fator_invalido():
    falso, fabrica = _watsonx(
        [("explicar_fator", {"fator": "pontualidade"}), ("explicar_fator", {"fator": "x"})]
    )
    operadora, consumidor, _ = _montar(fabrica)
    _, h = _com_score(operadora, consumidor, "carlos")

    r = consumidor.post("/assistente", json=PERGUNTA, headers=h)

    assert r.status_code == 200
    ok, invalido = falso.resultados()
    assert ok["fator"]["chave"] == "pontualidade"
    assert ok["formula"]["id"] == "pontualidade" and ok["formula"]["formula"]
    assert "erro" in invalido
    assert r.json()["ferramentas"][1]["erro"]


def test_simulacao_nao_altera_o_score_guardado():
    falso, fabrica = _watsonx([("simular_alteracao", {"valor_solicitado": 400})])
    operadora, consumidor, _ = _montar(fabrica)
    _, h = _com_score(operadora, consumidor, "ana")
    antes = consumidor.get("/meu-score", headers=h).json()

    r = consumidor.post("/assistente", json=PERGUNTA, headers=h)

    assert r.status_code == 200
    (sim,) = falso.resultados()
    assert sim["simulacao"] is True and "telefone" not in sim
    assert sim["oferta"] is None or sim["oferta"]["valor_ofertado"] <= 400
    assert consumidor.get("/meu-score", headers=h).json() == antes


def test_simulacao_sem_consentimento_da_erro_para_o_modelo():
    falso, fabrica = _watsonx([("simular_alteracao", {"valor_solicitado": 400})])
    operadora, consumidor, _ = _montar(fabrica)
    p = _cadastrar(operadora, consumidor, "maria")

    r = consumidor.post("/assistente", json=PERGUNTA, headers=_entrar(consumidor, p["cpf"]))

    assert r.status_code == 200
    assert "erro" in falso.resultados()[0]


def test_orchestrate_recebe_so_o_contexto_do_proprio_cliente():
    pedidos: list[dict] = []

    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.host == "iam.cloud.ibm.com":
            return httpx.Response(200, json={"access_token": "t", "expiration": 9e9})
        pedidos.append(json.loads(request.content))
        mensagem = {"role": "assistant", "content": "Explicação."}
        return httpx.Response(200, json={"model": "consultor_scorelyne", "choices": [{"message": mensagem}]})

    config = ConfigOrchestrate("https://wxo/instances/i", "k", "ag-consumidor")
    operadora, consumidor, _ = _montar(lambda: AssistenteOrchestrate(config, httpx.MockTransport(responder)))
    maria, h_maria = _com_score(operadora, consumidor, "maria")
    joao, h_joao = _com_score(operadora, consumidor, "joao")

    r = consumidor.post("/assistente", json=PERGUNTA, headers=h_maria)

    assert r.status_code == 200, r.text
    assert r.json()["provedor"] == "watsonx Orchestrate" and r.json()["ferramentas"] == []
    enviado = json.dumps(pedidos[0], ensure_ascii=False)
    sistema, usuario = pedidos[0]["messages"]
    assert sistema["role"] == "system" and usuario["content"] == PERGUNTA["mensagens"][0]["texto"]
    score_maria = consumidor.get("/meu-score", headers=h_maria).json()["analise"]["score"]
    score_joao = consumidor.get("/meu-score", headers=h_joao).json()["analise"]["score"]
    assert f'"score": {score_maria}' in sistema["content"]
    for segredo in (maria["telefone"], maria["cpf"], joao["telefone"], joao["cpf"]):
        assert segredo not in enviado
    if score_joao != score_maria:
        assert f'"score": {score_joao}' not in sistema["content"]


def test_orchestrate_sem_score_avisa_que_nao_ha_dados():
    pedidos: list[dict] = []

    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.host == "iam.cloud.ibm.com":
            return httpx.Response(200, json={"access_token": "t", "expiration": 9e9})
        pedidos.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]})

    config = ConfigOrchestrate("https://wxo/instances/i", "k", "ag")
    operadora, consumidor, _ = _montar(lambda: AssistenteOrchestrate(config, httpx.MockTransport(responder)))
    p = _cadastrar(operadora, consumidor, "maria")

    consumidor.post("/assistente", json=PERGUNTA, headers=_entrar(consumidor, p["cpf"]))

    assert "ainda não calculou o score" in pedidos[0]["messages"][0]["content"]


def test_assistente_exige_login_e_fica_desligado_sem_credenciais(monkeypatch):
    monkeypatch.delenv("WATSONX_APIKEY", raising=False)
    operadora, consumidor, _ = _montar()
    assert consumidor.get("/assistente").status_code == 401
    assert consumidor.post("/assistente", json=PERGUNTA).status_code == 401

    p = _cadastrar(operadora, consumidor, "maria")
    h = _entrar(consumidor, p["cpf"])
    status = consumidor.get("/assistente", headers=h).json()
    assert status["disponivel"] is False and len(status["perguntas"]) == 4
    assert consumidor.post("/assistente", json=PERGUNTA, headers=h).status_code == 503


@pytest.mark.parametrize("ferramenta", agente.FERRAMENTAS, ids=lambda f: f.nome)
def test_nenhuma_ferramenta_recebe_identificador_de_cliente(ferramenta):
    props = ferramenta.parametros.get("properties", {})
    assert not {"cliente_id", "cpf", "telefone", "consentimento_id", "id"} & set(props)


def test_agente_do_orchestrate_do_consumidor_nao_tem_ferramentas():
    definicao = yaml.safe_load(gerar_agente("watsonx-orchestrate/frontier"))
    assert definicao["kind"] == "native" and definicao["tools"] == []
    assert definicao["instructions"].startswith(agente.INSTRUCOES)
