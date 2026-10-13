import pytest
from fastapi.testclient import TestClient

from scorelyne.operadora.api import create_app

TODOS = ["recargas", "permanencia", "pontualidade", "estabilidade", "consistencia"]


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(tamanho_populacao=100, semente=1, demo=True))


@pytest.fixture(scope="module")
def maria(client):
    return next(p for p in client.get("/demo/personas").json() if p["chave"] == "maria")


def consentir(client, pessoa, escopos=TODOS):
    r = client.post(
        "/consentimentos",
        json={
            "telefone": pessoa["telefone"],
            "cpf": pessoa["cpf"],
            "escopos": escopos,
            "finalidade": "analise_de_credito",
            "solicitante": "Banco Parceiro",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_saude(client):
    assert client.get("/saude").json()["linhas"] == 105


def test_dados_exigem_consentimento(client, maria):
    r = client.get(f"/linhas/{maria['telefone']}/dados")
    assert r.status_code == 401


def test_cpf_errado_e_recusado(client, maria):
    r = client.post(
        "/consentimentos",
        json={
            "telefone": maria["telefone"],
            "escopos": TODOS,
            "cpf": "00000000000",
            "finalidade": "analise_de_credito",
            "solicitante": "Banco",
        },
    )
    assert r.status_code == 403


def test_devolve_so_escopos_autorizados(client, maria):
    cid = consentir(client, maria, ["recargas", "permanencia"])
    dados = client.get(f"/linhas/{maria['telefone']}/dados", headers={"X-Consentimento-Id": cid}).json()
    assert set(dados) >= {"recargas", "permanencia"}
    assert not {"pontualidade", "estabilidade", "consistencia"} & set(dados)
    assert len(dados["recargas"]["datas"]) == 71
    assert dados["permanencia"]["meses_na_base"] == 74


def test_consentimento_nao_vale_para_outra_linha(client, maria):
    cid = consentir(client, maria)
    outra = client.get("/demo/linhas?limite=1").json()[0]
    r = client.get(f"/linhas/{outra['telefone']}/dados", headers={"X-Consentimento-Id": cid})
    assert r.status_code == 403


def test_revogacao_bloqueia_novos_acessos_e_acessos_ficam_auditados(client, maria):
    cid = consentir(client, maria)
    url = f"/linhas/{maria['telefone']}/dados"
    assert client.get(url, headers={"X-Consentimento-Id": cid}).status_code == 200
    assert client.delete(f"/consentimentos/{cid}").json()["revogado_em"]
    assert client.get(url, headers={"X-Consentimento-Id": cid}).status_code == 403
    assert len(client.get(f"/consentimentos/{cid}").json()["acessos"]) == 1


def test_consistencia_e_agregada_por_mes(client):
    joao = next(p for p in client.get("/demo/personas").json() if p["chave"] == "joao")
    cid = consentir(client, joao, ["consistencia"])
    dados = client.get(f"/linhas/{joao['telefone']}/dados", headers={"X-Consentimento-Id": cid}).json()
    meses = dados["consistencia"]["valores_mensais"]
    assert sum(1 for m in meses if m["valor_fatura"] is not None) == 38
    assert all(45 <= m["valor_fatura"] <= 55 for m in meses if m["valor_fatura"] is not None)
