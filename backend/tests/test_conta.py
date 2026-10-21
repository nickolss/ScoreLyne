"""Controle dos próprios dados: consentimentos com histórico de acessos, pedidos, senha e exclusão da conta."""

import httpx
import pytest
from fastapi.testclient import TestClient

from scorelyne.consumidor.api import create_app as criar_consumidor
from scorelyne.operadora.api import create_app as criar_operadora
from tests.conftest import CHAVE_SERVICO, SENHA_ANALISTA
from tests.test_consumidor import SENHA, TODOS, _cadastrar, _entrar, _Ponte
from tests.test_consumidor_credor import PEDIDO, _com_score, mundo  # noqa: F401  (fixture reaproveitada)

# --- consentimentos e histórico de acessos ---------------------------------------------


def test_consentimentos_mostram_quem_leu_os_dados_e_quando(mundo):  # noqa: F811
    operadora, consumidor, _ = mundo
    _, h = _com_score(operadora, consumidor, "maria")

    so_scorelyne = consumidor.get("/meus-consentimentos", headers=h).json()
    assert [c["destinatario"] for c in so_scorelyne] == ["ScoreLyne"]
    assert so_scorelyne[0]["finalidade"] == "autoconsulta_de_score"
    assert len(so_scorelyne[0]["acessos"]) == 1  # o cálculo do próprio score
    assert set(so_scorelyne[0]["acessos"][0]["escopos"]) == set(TODOS)

    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()
    ambos = {c["destinatario"]: c for c in consumidor.get("/meus-consentimentos", headers=h).json()}
    assert set(ambos) == {"ScoreLyne", "Banco Parceiro S.A."}
    assert ambos["Banco Parceiro S.A."]["finalidade"] == "analise_de_credito"
    assert len(ambos["Banco Parceiro S.A."]["acessos"]) == 1  # o credor leu uma vez, ao criar o pedido


def test_cada_pessoa_ve_so_os_proprios_consentimentos(mundo):  # noqa: F811
    operadora, consumidor, _ = mundo
    _com_score(operadora, consumidor, "maria")
    joao = _cadastrar(operadora, consumidor, "joao")
    h_joao = _entrar(consumidor, joao["cpf"])

    assert consumidor.get("/meus-consentimentos", headers=h_joao).json() == []
    assert consumidor.get("/meus-pedidos", headers=h_joao).json() == []


def test_revogar_zera_a_lista_de_consentimentos(mundo):  # noqa: F811
    operadora, consumidor, _ = mundo
    _, h = _com_score(operadora, consumidor, "maria")
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()

    consumidor.post("/revogar", headers=h).raise_for_status()

    assert consumidor.get("/meus-consentimentos", headers=h).json() == []


# --- histórico de pedidos ---------------------------------------------------------------


def test_historico_de_pedidos_guarda_o_que_foi_retirado_e_reenviado(mundo):  # noqa: F811
    operadora, consumidor, _ = mundo
    _, h = _com_score(operadora, consumidor, "maria")
    assert consumidor.get("/meus-pedidos", headers=h).json() == []

    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()
    (aberto,) = consumidor.get("/meus-pedidos", headers=h).json()
    assert aberto["encerrado_em"] is None and aberto["valor_solicitado"] == PEDIDO["valor_solicitado"]
    assert aberto["situacao"]["status"] == "aprovado"

    consumidor.post("/retirar-do-credor", headers=h).raise_for_status()
    (retirado,) = consumidor.get("/meus-pedidos", headers=h).json()
    assert retirado["encerramento"] == "retirado_pelo_cliente"
    assert retirado["encerrado_em"] is not None and retirado["situacao"] is None

    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()
    novo, antigo = consumidor.get("/meus-pedidos", headers=h).json()  # o mais recente primeiro
    assert novo["encerrado_em"] is None and antigo["encerramento"] == "retirado_pelo_cliente"


def test_trocar_telefone_encerra_o_pedido_como_dados_alterados(mundo):  # noqa: F811
    operadora, consumidor, _ = mundo
    _, h = _com_score(operadora, consumidor, "maria")
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()

    consumidor.patch("/meus-dados", json={"telefone": "11900000000"}, headers=h).raise_for_status()

    (p,) = consumidor.get("/meus-pedidos", headers=h).json()
    assert p["encerramento"] == "dados_alterados" and p["situacao"] is None


def test_revogar_encerra_o_pedido_como_consentimento_revogado(mundo):  # noqa: F811
    operadora, consumidor, _ = mundo
    _, h = _com_score(operadora, consumidor, "maria")
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()

    consumidor.post("/revogar", headers=h).raise_for_status()

    (p,) = consumidor.get("/meus-pedidos", headers=h).json()
    assert p["encerramento"] == "consentimento_revogado"


# --- troca de senha --------------------------------------------------------------------


def test_trocar_senha_exige_a_atual_e_vale_so_a_nova(mundo):  # noqa: F811
    operadora, consumidor, _ = mundo
    p = _cadastrar(operadora, consumidor, "maria")
    h = _entrar(consumidor, p["cpf"])
    url = "/minha-conta/senha"

    assert (
        consumidor.post(
            url, json={"senha_atual": "errada-123", "nova_senha": "outra-senha-1"}, headers=h
        ).status_code
        == 403
    )
    assert (
        consumidor.post(url, json={"senha_atual": SENHA, "nova_senha": SENHA}, headers=h).status_code == 422
    )
    assert (
        consumidor.post(url, json={"senha_atual": SENHA, "nova_senha": "curta"}, headers=h).status_code == 422
    )
    assert (
        consumidor.post(
            url, json={"senha_atual": SENHA, "nova_senha": "outra-senha-1"}, headers=h
        ).status_code
        == 200
    )

    assert consumidor.post("/login", json={"cpf": p["cpf"], "senha": SENHA}).status_code == 401
    assert consumidor.post("/login", json={"cpf": p["cpf"], "senha": "outra-senha-1"}).status_code == 200


def test_trocar_senha_exige_login(mundo):  # noqa: F811
    _, consumidor, _ = mundo
    r = consumidor.post("/minha-conta/senha", json={"senha_atual": "x", "nova_senha": "outra-senha-1"})
    assert r.status_code == 401


# --- exclusão da conta ------------------------------------------------------------------


def test_excluir_conta_pede_senha_e_nao_apaga_com_senha_errada(mundo):  # noqa: F811
    operadora, consumidor, _ = mundo
    p = _cadastrar(operadora, consumidor, "maria")
    h = _entrar(consumidor, p["cpf"])

    assert consumidor.post("/minha-conta/excluir", json={"senha": "errada-123"}, headers=h).status_code == 403
    assert consumidor.get("/me", headers=h).status_code == 200


def test_excluir_conta_revoga_tudo_e_apaga_o_cadastro(mundo):  # noqa: F811
    operadora, consumidor, analista = mundo
    p, h = _com_score(operadora, consumidor, "maria")
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()
    ids = [c["id"] for c in consumidor.get("/meus-consentimentos", headers=h).json()]
    sid = analista.get("/solicitacoes").json()[0]["id"]

    r = consumidor.post("/minha-conta/excluir", json={"senha": SENHA}, headers=h)

    assert r.status_code == 200 and r.json() == {"excluida": True}
    assert consumidor.get("/me", headers=h).status_code == 401  # o token antigo não vale mais
    assert consumidor.post("/login", json={"cpf": p["cpf"], "senha": SENHA}).status_code == 401
    assert all(operadora.get(f"/consentimentos/{i}").json()["revogado_em"] for i in ids)
    revogada = analista.get(f"/solicitacoes/{sid}").json()
    assert revogada["status"] == "revogado" and revogada["analise"] is None

    # dá para se cadastrar de novo com o mesmo CPF: nada ficou para trás
    assert _cadastrar(operadora, consumidor, "maria")["cpf"] == p["cpf"]


class _PonteInstavel(_Ponte):
    """Ponte para o credor que pode 'cair', como se o serviço estivesse fora do ar."""

    fora_do_ar = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self.fora_do_ar:
            raise httpx.ConnectError("credor fora do ar", request=request)
        return super().handle_request(request)


def test_excluir_conta_com_credor_fora_do_ar_ainda_bloqueia_o_acesso_dele(credor):
    operadora = TestClient(criar_operadora(tamanho_populacao=50, semente=1, demo=True))
    analista = credor(db_url="sqlite://", operadora_url="http://operadora", transporte=_Ponte(operadora))
    ponte = _PonteInstavel(TestClient(analista.app))
    consumidor = TestClient(
        criar_consumidor(
            db_url="sqlite://",
            operadora_url="http://operadora",
            transporte=_Ponte(operadora),
            credor_url="http://credor",
            transporte_credor=ponte,
            chave_servico=CHAVE_SERVICO,
            segredo="segredo-de-teste-com-32-bytes-ou-mais!!",
        )
    )
    _, h = _com_score(operadora, consumidor, "maria")
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()
    ids = [c["id"] for c in consumidor.get("/meus-consentimentos", headers=h).json()]
    ponte.fora_do_ar = True

    r = consumidor.post("/minha-conta/excluir", json={"senha": SENHA}, headers=h)

    assert r.status_code == 200, r.text
    # Mesmo sem falar com o credor, a operadora passou a barrar a leitura dos dados pelos dois.
    assert all(operadora.get(f"/consentimentos/{i}").json()["revogado_em"] for i in ids)


def test_excluir_conta_exige_login(mundo):  # noqa: F811
    _, consumidor, _ = mundo
    assert consumidor.post("/minha-conta/excluir", json={"senha": SENHA}).status_code == 401


# --- perfil do analista -----------------------------------------------------------------


def test_analista_ve_o_proprio_perfil(mundo):  # noqa: F811
    *_, analista = mundo
    assert analista.get("/eu").json() == {"nome": "Ana Analista", "email": "ana@teste.com"}
    assert TestClient(analista.app).get("/eu").status_code in (401, 403)


def test_analista_troca_a_senha(mundo):  # noqa: F811
    *_, analista = mundo
    anonimo = TestClient(analista.app)
    url = "/minha-conta/senha"
    assert (
        analista.post(url, json={"senha_atual": "errada-123", "nova_senha": "outra-senha-1"}).status_code
        == 403
    )
    assert (
        analista.post(url, json={"senha_atual": SENHA_ANALISTA, "nova_senha": "outra-senha-1"}).status_code
        == 200
    )

    assert anonimo.post("/login", json={"email": "ana@teste.com", "senha": SENHA_ANALISTA}).status_code == 401
    assert (
        anonimo.post("/login", json={"email": "ana@teste.com", "senha": "outra-senha-1"}).status_code == 200
    )


@pytest.mark.parametrize("caminho", ["/eu", "/minha-conta/senha"])
def test_rotas_do_perfil_do_analista_exigem_login(mundo, caminho):  # noqa: F811
    *_, analista = mundo
    anonimo = TestClient(analista.app)
    r = anonimo.get(caminho) if caminho == "/eu" else anonimo.post(caminho, json={})
    assert r.status_code in (401, 403)
