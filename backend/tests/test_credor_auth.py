import pytest
from fastapi.testclient import TestClient

from scorelyne.banco.api import create_app
from scorelyne.comum.auth import Autenticador
from tests.conftest import CHAVE_AGENTE, CHAVE_SERVICO, SEGREDO, SENHA_ANALISTA

PROTEGIDAS = [
    ("get", "/solicitacoes"),
    ("get", "/solicitacoes/qualquer"),
    ("post", "/solicitacoes"),
    ("post", "/solicitacoes/qualquer/decisao"),
    ("delete", "/solicitacoes/qualquer/decisao"),
    ("post", "/solicitacoes/qualquer/revogar"),
    ("post", "/analises"),
    ("post", "/analises/dados"),
    ("get", "/copiloto"),
    ("post", "/copiloto"),
]


@pytest.fixture
def anonimo(credor):
    """Mesmo app do credor, mas sem nenhuma credencial."""
    app = credor(db_url="sqlite://").app
    return TestClient(app), app


def test_rotas_protegidas_barram_quem_nao_se_identifica(anonimo):
    cliente, _ = anonimo
    for metodo, caminho in PROTEGIDAS:
        r = getattr(cliente, metodo)(caminho)
        assert r.status_code in (401, 403), (metodo, caminho, r.status_code)


def test_so_saude_login_e_modelo_sao_publicos(anonimo):
    cliente, _ = anonimo
    assert cliente.get("/saude").status_code == 200
    assert cliente.get("/modelo").status_code == 200


def test_login_do_analista(anonimo):
    cliente, _ = anonimo
    ok = cliente.post("/login", json={"email": "ANA@teste.com", "senha": SENHA_ANALISTA})
    assert ok.status_code == 200 and ok.json()["nome"] == "Ana Analista"
    token = ok.json()["token"]
    assert cliente.get("/solicitacoes", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    errada = cliente.post("/login", json={"email": "ana@teste.com", "senha": "errada-123"})
    desconhecido = cliente.post("/login", json={"email": "ninguem@teste.com", "senha": SENHA_ANALISTA})
    assert errada.status_code == desconhecido.status_code == 401
    assert errada.json() == desconhecido.json()


def test_token_do_consumidor_nao_vale_no_credor(anonimo):
    cliente, _ = anonimo
    # Mesmo com o segredo certo, o papel do token não é "analista"
    token = Autenticador("consumidor", SEGREDO).criar_token("qualquer-id")
    r = cliente.get("/solicitacoes", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_agente_so_le_e_simula(anonimo):
    cliente, _ = anonimo
    h = {"X-Agent-Key": CHAVE_AGENTE}
    assert cliente.get("/solicitacoes", headers=h).status_code == 200
    assert cliente.post("/analises/dados", headers=h, json={}).status_code == 422  # passou da auth
    for metodo, caminho in [
        ("post", "/solicitacoes/qualquer/decisao"),
        ("delete", "/solicitacoes/qualquer/decisao"),
        ("post", "/solicitacoes/qualquer/revogar"),
        ("post", "/solicitacoes"),
        ("get", "/copiloto"),
    ]:
        assert getattr(cliente, metodo)(caminho, headers=h).status_code in (401, 403), caminho
    assert cliente.get("/solicitacoes", headers={"X-Agent-Key": "chave-errada"}).status_code == 401


def test_chave_do_agente_desligada_quando_nao_configurada(monkeypatch):
    monkeypatch.delenv("CREDOR_AGENT_KEY", raising=False)
    app = create_app(db_url="sqlite://", segredo=SEGREDO, chave_servico=CHAVE_SERVICO)
    r = TestClient(app).get("/solicitacoes", headers={"X-Agent-Key": ""})
    assert r.status_code == 401


def test_servico_cria_e_revoga_mas_nao_decide(anonimo):
    cliente, _ = anonimo
    h = {"X-Service-Key": CHAVE_SERVICO}
    # Passa pela auth (corpo vazio vira 422) mas não pela decisão do analista
    assert cliente.post("/solicitacoes", headers=h, json={}).status_code == 422
    assert cliente.post("/solicitacoes/x/decisao", headers=h, json={}).status_code == 401
    assert cliente.post("/solicitacoes", headers={"X-Service-Key": "errada"}, json={}).status_code == 403
