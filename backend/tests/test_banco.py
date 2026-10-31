import json

import httpx
import pytest
from fastapi.testclient import TestClient

from scorelyne.operadora.api import create_app as criar_operadora

TODOS = ["recargas", "permanencia", "pontualidade", "estabilidade", "consistencia"]


class _Ponte(httpx.BaseTransport):
    """Encaminha as chamadas do banco para o TestClient da operadora."""

    def __init__(self, cliente: TestClient):
        self.cliente = cliente

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        r = self.cliente.request(request.method, request.url.path, headers=dict(request.headers))
        return httpx.Response(r.status_code, content=r.content, headers=r.headers)


@pytest.fixture
def apis(credor):
    operadora = TestClient(criar_operadora(tamanho_populacao=50, semente=1, demo=True))
    banco = credor(db_url="sqlite://", operadora_url="http://operadora", transporte=_Ponte(operadora))
    return operadora, banco


def _pedir(operadora, banco, chave, escopos=TODOS, valor=1500):
    p = next(x for x in operadora.get("/demo/personas").json() if x["chave"] == chave)
    cid = operadora.post(
        "/consentimentos",
        json={
            "telefone": p["telefone"],
            "cpf": p["cpf"],
            "escopos": escopos,
            "finalidade": "analise_de_credito",
            "solicitante": "Banco",
        },
    ).json()["id"]
    return banco.post(
        "/solicitacoes",
        json={
            "nome": p["titular"],
            "telefone": p["telefone"],
            "consentimento_id": cid,
            "valor_solicitado": valor,
            "finalidade": "Equipamentos",
            "ocupacao": "Autônoma",
            "cidade": p["cidade"],
            "uf": p["uf"],
        },
    )


def test_cria_solicitacao_com_analise_e_trilha(apis):
    operadora, banco = apis
    r = _pedir(operadora, banco, "maria")
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["status"] == "aprovado"
    assert s["analise"]["oferta"]["valor_ofertado"] == 1500
    assert s["plano"] == "pre_pago"
    assert [e["tipo"] for e in s["eventos"]] == [
        "consentimento",
        "dados_recebidos",
        "score",
        "equidade",
        "decisao_agente",
    ]
    assert [x["id"] for x in banco.get("/solicitacoes").json()] == [s["id"]]


def test_analista_decide_revisao_e_pode_desfazer(apis):
    operadora, banco = apis
    s = _pedir(operadora, banco, "luciana", valor=1000).json()
    assert s["status"] == "revisao"
    assert [x["id"] for x in banco.get("/solicitacoes?status=revisao").json()] == [s["id"]]

    curta = banco.post(
        f"/solicitacoes/{s['id']}/decisao", json={"veredito": "aprovar", "justificativa": "ok"}
    )
    assert curta.status_code == 422

    d = banco.post(
        f"/solicitacoes/{s['id']}/decisao",
        json={"veredito": "aprovar", "justificativa": "Recargas regulares compensam o tempo curto de base"},
    ).json()
    assert d["status"] == "aprovado"
    assert d["revisao_humana"]["veredito"] == "aprovar"
    assert d["eventos"][-1]["tipo"] == "decisao_analista"

    desfeito = banco.delete(f"/solicitacoes/{s['id']}/decisao").json()
    assert desfeito["status"] == "revisao" and desfeito["revisao_humana"] is None
    assert desfeito["eventos"][-1]["tipo"] == "decisao_desfeita"


def test_decisao_registra_o_analista_do_login_e_nao_o_do_corpo(apis):
    operadora, banco = apis
    s = _pedir(operadora, banco, "luciana", valor=1000).json()
    d = banco.post(
        f"/solicitacoes/{s['id']}/decisao",
        json={
            "veredito": "aprovar",
            "justificativa": "Recargas regulares compensam o tempo curto de base",
            "analista": "Outra Pessoa",
        },
    ).json()
    assert d["revisao_humana"]["analista"] == "Ana Analista"


def test_analista_pode_sobrepor_o_agente(apis):
    operadora, banco = apis
    s = _pedir(operadora, banco, "carlos", valor=5000).json()
    assert s["status"] == "recusado"
    d = banco.post(
        f"/solicitacoes/{s['id']}/decisao",
        json={"veredito": "aprovar", "justificativa": "Atrasos explicados por internação, comprovada"},
    ).json()
    assert d["status"] == "aprovado"
    assert "sobrepondo o agente" in d["eventos"][-1]["titulo"]


def test_revogacao_apaga_analise_e_bloqueia_operadora(apis):
    operadora, banco = apis
    s = _pedir(operadora, banco, "joao").json()
    r = banco.post(f"/solicitacoes/{s['id']}/revogar").json()
    assert r["status"] == "revogado"
    assert r["analise"] is None and r["score"] is None
    assert operadora.get(f"/consentimentos/{s['consentimento_id']}").json()["revogado_em"]
    decidir = banco.post(
        f"/solicitacoes/{s['id']}/decisao", json={"veredito": "aprovar", "justificativa": "tentativa depois"}
    )
    assert decidir.status_code == 409


def test_sem_escopo_obrigatorio_e_422(apis):
    operadora, banco = apis
    r = _pedir(operadora, banco, "maria", escopos=["permanencia", "recargas"])
    assert r.status_code == 422


def test_analise_avulsa_repassa_revogacao(apis):
    operadora, banco = apis
    p = next(x for x in operadora.get("/demo/personas").json() if x["chave"] == "joao")
    cid = operadora.post(
        "/consentimentos",
        json={
            "telefone": p["telefone"],
            "cpf": p["cpf"],
            "escopos": TODOS,
            "finalidade": "analise_de_credito",
            "solicitante": "Banco",
        },
    ).json()["id"]
    assert (
        banco.post("/analises", json={"telefone": p["telefone"], "consentimento_id": cid}).status_code == 200
    )
    operadora.delete(f"/consentimentos/{cid}")
    r = banco.post("/analises", json={"telefone": p["telefone"], "consentimento_id": cid})
    assert r.status_code == 403 and "revogado" in r.json()["detail"]


def test_cartao_do_modelo(apis):
    _, banco = apis
    cartao = banco.get("/modelo").json()
    fatores = {f["chave"]: f for f in cartao["fatores"]}
    assert fatores["estabilidade"]["perda_maxima_se_omitir"] == 0
    assert fatores["consistencia"]["perda_maxima_se_omitir"] > 0
    assert fatores["pontualidade"]["obrigatorio"]


class _WatsonxFalso(httpx.BaseTransport):
    """Simula o IAM e o chat do watsonx.ai: pede uma ferramenta e depois responde em texto."""

    def __init__(self):
        self.corpos: list[dict] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "iam.cloud.ibm.com":
            return httpx.Response(200, json={"access_token": "t", "expiration": 9e9})
        corpo = json.loads(request.content)
        self.corpos.append(corpo)
        if len(self.corpos) == 1:
            chamada = {
                "id": "c1",
                "type": "function",
                "function": {"name": "listar_solicitacoes", "arguments": '{"status": "revisao"}'},
            }
            mensagem = {"role": "assistant", "content": "", "tool_calls": [chamada]}
        else:
            mensagem = {"role": "assistant", "content": "A Luciana está em revisão."}
        return httpx.Response(200, json={"choices": [{"message": mensagem}]})


def test_copiloto_chama_ferramenta_e_responde(credor):
    from scorelyne.banco.copiloto import ConfigWatsonx, Watsonx

    operadora = TestClient(criar_operadora(tamanho_populacao=50, semente=1, demo=True))
    falso = _WatsonxFalso()
    banco = credor(
        db_url="sqlite://",
        operadora_url="http://operadora",
        transporte=_Ponte(operadora),
        assistente=Watsonx(ConfigWatsonx("http://wx", "k", "p", None, "ibm/granite-4-h-small"), falso),
    )
    _pedir(operadora, banco, "luciana")

    r = banco.post("/copiloto", json={"mensagens": [{"papel": "analista", "texto": "Quem está em revisão?"}]})

    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["resposta"] == "A Luciana está em revisão."
    assert corpo["ferramentas"] == [
        {"nome": "listar_solicitacoes", "argumentos": {"status": "revisao"}, "erro": None}
    ]
    resultado = json.loads(falso.corpos[1]["messages"][-1]["content"])
    assert [x["status"] for x in resultado] == ["revisao"]
    assert falso.corpos[0]["project_id"] == "p"


def test_copiloto_desligado_sem_credenciais(monkeypatch, credor):
    monkeypatch.delenv("WATSONX_APIKEY", raising=False)
    banco = credor(db_url="sqlite://", operadora_url="http://operadora")
    status = banco.get("/copiloto").json()
    assert status["disponivel"] is False and status["provedor"] is None
    assert len(status["perguntas"]) == 4
    r = banco.post("/copiloto", json={"mensagens": [{"papel": "analista", "texto": "oi"}]})
    assert r.status_code == 503


def test_copiloto_via_orchestrate(credor):
    from scorelyne.banco.copiloto import ConfigOrchestrate, Orchestrate

    pedidos: list[httpx.Request] = []

    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.host == "iam.cloud.ibm.com":
            return httpx.Response(200, json={"access_token": "t", "expiration": 9e9})
        pedidos.append(request)
        mensagem = {"role": "assistant", "content": "Versão 20261013-s42."}
        return httpx.Response(
            200, json={"model": "watsonx-orchestrate/frontier", "choices": [{"message": mensagem}]}
        )

    assistente = Orchestrate(
        ConfigOrchestrate("https://wxo/instances/i", "k", "ag1"), httpx.MockTransport(responder)
    )
    banco = credor(db_url="sqlite://", operadora_url="http://operadora", assistente=assistente)

    assert banco.get("/copiloto").json()["provedor"] == "watsonx Orchestrate"
    r = banco.post(
        "/copiloto",
        json={
            "mensagens": [
                {"papel": "analista", "texto": "Qual a versão?"},
                {"papel": "copiloto", "texto": "Vou ver."},
                {"papel": "analista", "texto": "E então?"},
            ]
        },
    )

    assert r.status_code == 200, r.text
    assert r.json()["resposta"] == "Versão 20261013-s42."
    assert r.json()["modelo"] == "watsonx-orchestrate/frontier"
    assert pedidos[0].url.path == "/instances/i/v1/orchestrate/ag1/chat/completions"
    assert pedidos[0].headers["authorization"] == "Bearer t"
    papeis = [m["role"] for m in json.loads(pedidos[0].content)["messages"]]
    assert papeis == ["user", "assistant", "user"]
