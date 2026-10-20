import httpx
import pytest
from fastapi.testclient import TestClient

from scorelyne.comum.auth import Autenticador, hash_senha, senha_confere
from scorelyne.consumidor.api import create_app as criar_consumidor
from scorelyne.operadora.api import create_app as criar_operadora

SENHA = "senha-forte-123"
TODOS = ["recargas", "permanencia", "pontualidade", "estabilidade", "consistencia"]


class _Ponte(httpx.BaseTransport):
    """Encaminha as chamadas do consumidor para o TestClient da operadora."""

    def __init__(self, cliente: TestClient):
        self.cliente = cliente

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        r = self.cliente.request(
            request.method, request.url.path, headers=dict(request.headers), content=request.content
        )
        return httpx.Response(r.status_code, content=r.content, headers=r.headers)


@pytest.fixture
def apis():
    operadora = TestClient(criar_operadora(tamanho_populacao=50, semente=1, demo=True))
    consumidor = TestClient(
        criar_consumidor(
            db_url="sqlite://",
            operadora_url="http://operadora",
            transporte=_Ponte(operadora),
            segredo="segredo-de-teste-com-32-bytes-ou-mais!!",
        )
    )
    return operadora, consumidor


def _persona(operadora, chave):
    return next(p for p in operadora.get("/demo/personas").json() if p["chave"] == chave)


def _cadastrar(operadora, consumidor, chave="maria"):
    p = _persona(operadora, chave)
    r = consumidor.post(
        "/cadastro",
        json={
            "nome": p["titular"],
            "cpf": p["cpf"],
            "telefone": p["telefone"],
            "senha": SENHA,
            "ocupacao": "Autônoma",
            "cidade": p["cidade"],
            "uf": p["uf"],
        },
    )
    assert r.status_code == 201, r.text
    return p


def _entrar(consumidor, cpf):
    r = consumidor.post("/login", json={"cpf": cpf, "senha": SENHA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_senha_nunca_fica_em_texto_puro():
    h = hash_senha(SENHA)
    assert SENHA not in h
    assert senha_confere(SENHA, h)
    assert not senha_confere("outra-senha", h)
    assert hash_senha(SENHA) != h  # sal diferente a cada hash


def test_cadastro_rejeita_cpf_invalido_e_duplicado(apis):
    operadora, consumidor = apis
    p = _cadastrar(operadora, consumidor)
    corpo = {"nome": "Fulano", "cpf": "12345678900", "telefone": "11911112222", "senha": SENHA}
    assert consumidor.post("/cadastro", json=corpo).status_code == 422
    repetido = {**corpo, "cpf": p["cpf"], "telefone": "11911112222"}
    assert consumidor.post("/cadastro", json=repetido).status_code == 409


def test_login_nao_revela_se_o_cpf_existe(apis):
    operadora, consumidor = apis
    p = _cadastrar(operadora, consumidor)
    senha_errada = consumidor.post("/login", json={"cpf": p["cpf"], "senha": "errada-123"})
    desconhecido = consumidor.post("/login", json={"cpf": "52998224725", "senha": SENHA})
    assert senha_errada.status_code == desconhecido.status_code == 401
    assert senha_errada.json() == desconhecido.json()


def test_rotas_exigem_token(apis):
    _, consumidor = apis
    for metodo, caminho in [("get", "/me"), ("get", "/meu-score"), ("post", "/revogar")]:
        assert getattr(consumidor, metodo)(caminho).status_code == 401


def test_token_de_outro_papel_ou_segredo_e_barrado(apis):
    operadora, consumidor = apis
    p = _cadastrar(operadora, consumidor)
    cid = consumidor.post("/login", json={"cpf": p["cpf"], "senha": SENHA}).json()["cliente"]["id"]

    analista = Autenticador("analista", "segredo-de-teste-com-32-bytes-ou-mais!!").criar_token(cid)
    r = consumidor.get("/me", headers={"Authorization": f"Bearer {analista}"})
    assert r.status_code == 403

    forjado = Autenticador("consumidor", "outro-segredo-tambem-com-32-bytes-ou-mais").criar_token(cid)
    r = consumidor.get("/me", headers={"Authorization": f"Bearer {forjado}"})
    assert r.status_code == 401


def test_jornada_completa_consentimento_score_e_revogacao(apis):
    operadora, consumidor = apis
    p = _cadastrar(operadora, consumidor)
    h = _entrar(consumidor, p["cpf"])

    # Sem consentimento não há score
    pedido = {"valor_solicitado": 1500, "finalidade": "Equipamentos"}
    assert consumidor.post("/meu-score", json=pedido, headers=h).status_code == 409
    assert consumidor.get("/meu-score", headers=h).status_code == 404

    r = consumidor.post("/consentimentos", json={"escopos": TODOS}, headers=h)
    assert r.status_code == 201, r.text
    assert consumidor.post("/consentimentos", json={"escopos": TODOS}, headers=h).status_code == 409

    r = consumidor.post("/meu-score", json=pedido, headers=h)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert 0 <= corpo["analise"]["score"] <= 1000
    assert corpo["analise"]["fatores"], "a explicação por fator precisa vir junto"
    assert consumidor.get("/meu-score", headers=h).json()["analise"]["score"] == corpo["analise"]["score"]

    # Revogar apaga o score e a operadora passa a barrar a leitura
    cliente = consumidor.post("/revogar", headers=h).json()
    assert cliente["consentimento_ativo"] is False
    assert consumidor.get("/meu-score", headers=h).status_code == 404
    assert operadora.get(f"/linhas/{p['telefone']}/dados").status_code == 401


def test_cada_consumidor_ve_so_os_proprios_dados(apis):
    operadora, consumidor = apis
    maria = _cadastrar(operadora, consumidor, "maria")
    joao = _cadastrar(operadora, consumidor, "joao")
    h_maria, h_joao = _entrar(consumidor, maria["cpf"]), _entrar(consumidor, joao["cpf"])

    consumidor.post("/consentimentos", json={"escopos": TODOS}, headers=h_maria)
    consumidor.post(
        "/meu-score", json={"valor_solicitado": 1000, "finalidade": "Teste"}, headers=h_maria
    ).raise_for_status()

    assert consumidor.get("/me", headers=h_joao).json()["telefone"] == joao["telefone"]
    assert consumidor.get("/meu-score", headers=h_joao).status_code == 404


def test_trocar_telefone_revoga_o_consentimento(apis):
    operadora, consumidor = apis
    p = _cadastrar(operadora, consumidor)
    h = _entrar(consumidor, p["cpf"])
    consumidor.post("/consentimentos", json={"escopos": TODOS}, headers=h).raise_for_status()
    consumidor.post(
        "/meu-score", json={"valor_solicitado": 1000, "finalidade": "Teste"}, headers=h
    ).raise_for_status()

    r = consumidor.patch("/meus-dados", json={"telefone": "11900000000", "ocupacao": "Costureira"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["consentimento_ativo"] is False
    assert r.json()["ocupacao"] == "Costureira"
    assert consumidor.get("/meu-score", headers=h).status_code == 404
