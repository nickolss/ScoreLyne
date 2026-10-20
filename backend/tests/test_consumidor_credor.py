"""Fluxo entre os dois módulos: o consumidor envia o pedido, o analista decide, o consumidor vê o resultado."""

import pytest
from fastapi.testclient import TestClient

from scorelyne.consumidor.api import create_app as criar_consumidor
from scorelyne.operadora.api import create_app as criar_operadora
from tests.conftest import CHAVE_SERVICO
from tests.test_consumidor import TODOS, _cadastrar, _entrar, _Ponte

PEDIDO = {"valor_solicitado": 1000, "finalidade": "Equipamentos"}


@pytest.fixture
def mundo(credor):
    """Operadora, credor e consumidor ligados. `analista` é o cliente do credor com token de analista."""
    operadora = TestClient(criar_operadora(tamanho_populacao=50, semente=1, demo=True))
    analista = credor(db_url="sqlite://", operadora_url="http://operadora", transporte=_Ponte(operadora))
    # O consumidor chega ao credor sem token de analista: só com a chave de serviço.
    sem_token = TestClient(analista.app)
    consumidor = TestClient(
        criar_consumidor(
            db_url="sqlite://",
            operadora_url="http://operadora",
            transporte=_Ponte(operadora),
            credor_url="http://credor",
            transporte_credor=_Ponte(sem_token),
            chave_servico=CHAVE_SERVICO,
            segredo="segredo-de-teste-com-32-bytes-ou-mais!!",
        )
    )
    return operadora, consumidor, analista


def _com_score(operadora, consumidor, chave):
    p = _cadastrar(operadora, consumidor, chave)
    h = _entrar(consumidor, p["cpf"])
    consumidor.post("/consentimentos", json={"escopos": TODOS}, headers=h).raise_for_status()
    consumidor.post("/meu-score", json=PEDIDO, headers=h).raise_for_status()
    return p, h


def test_enviar_pedido_aparece_na_fila_do_credor_e_a_situacao_volta_ao_consumidor(mundo):
    operadora, consumidor, analista = mundo
    _, h = _com_score(operadora, consumidor, "maria")

    r = consumidor.post("/enviar-ao-credor", headers=h)

    assert r.status_code == 200, r.text
    assert r.json()["enviado_ao_credor"] is True
    fila = analista.get("/solicitacoes").json()
    assert len(fila) == 1 and fila[0]["status"] == "aprovado"
    situacao = consumidor.get("/minha-solicitacao", headers=h).json()
    assert situacao["id"] == fila[0]["id"] and situacao["status"] == "aprovado"
    assert situacao["oferta"]["valor_ofertado"] == 1000
    assert "eventos" not in situacao and "telefone" not in situacao  # só o que é da própria pessoa


def test_decisao_do_analista_chega_ao_consumidor_com_a_justificativa(mundo):
    operadora, consumidor, analista = mundo
    _, h = _com_score(operadora, consumidor, "luciana")  # histórico curto: vai para revisão
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()
    sid = analista.get("/solicitacoes?status=revisao").json()[0]["id"]

    assert consumidor.get("/minha-solicitacao", headers=h).json()["status"] == "revisao"
    analista.post(
        f"/solicitacoes/{sid}/decisao",
        json={"veredito": "aprovar", "justificativa": "Recargas regulares compensam a base curta"},
    ).raise_for_status()

    situacao = consumidor.get("/minha-solicitacao", headers=h).json()
    assert situacao["status"] == "aprovado"
    assert situacao["revisao_humana"]["analista"] == "Ana Analista"
    assert "Recargas regulares" in situacao["revisao_humana"]["justificativa"]


def test_nao_envia_sem_score_nem_duas_vezes(mundo):
    operadora, consumidor, _ = mundo
    p = _cadastrar(operadora, consumidor, "maria")
    h = _entrar(consumidor, p["cpf"])
    assert consumidor.post("/enviar-ao-credor", headers=h).status_code == 409
    assert consumidor.get("/minha-solicitacao", headers=h).status_code == 404

    consumidor.post("/consentimentos", json={"escopos": TODOS}, headers=h).raise_for_status()
    consumidor.post("/meu-score", json=PEDIDO, headers=h).raise_for_status()
    assert consumidor.post("/enviar-ao-credor", headers=h).status_code == 200
    assert consumidor.post("/enviar-ao-credor", headers=h).status_code == 409


def test_credor_recebe_um_consentimento_proprio_e_so_dele(mundo):
    operadora, consumidor, analista = mundo
    _, h = _com_score(operadora, consumidor, "maria")
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()

    solicitacao = analista.get(f"/solicitacoes/{analista.get('/solicitacoes').json()[0]['id']}").json()
    consentimento = operadora.get(f"/consentimentos/{solicitacao['consentimento_id']}").json()
    assert consentimento["solicitante"] == "Banco Parceiro S.A."
    assert consentimento["finalidade"] == "analise_de_credito"
    assert consumidor.get("/me", headers=h).json()["enviado_ao_credor"] is True


def test_revogar_apaga_o_pedido_no_credor_e_bloqueia_a_operadora(mundo):
    operadora, consumidor, analista = mundo
    _, h = _com_score(operadora, consumidor, "maria")
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()
    sid = analista.get("/solicitacoes").json()[0]["id"]
    cid_credor = analista.get(f"/solicitacoes/{sid}").json()["consentimento_id"]

    cliente = consumidor.post("/revogar", headers=h).json()

    assert cliente["consentimento_ativo"] is False and cliente["enviado_ao_credor"] is False
    revogada = analista.get(f"/solicitacoes/{sid}").json()
    assert revogada["status"] == "revogado" and revogada["analise"] is None
    assert operadora.get(f"/consentimentos/{cid_credor}").json()["revogado_em"] is not None
    assert consumidor.get("/meu-score", headers=h).status_code == 404


def test_retirar_do_credor_mantem_o_score_e_permite_reenviar(mundo):
    operadora, consumidor, analista = mundo
    _, h = _com_score(operadora, consumidor, "maria")
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()
    sid = analista.get("/solicitacoes").json()[0]["id"]

    cliente = consumidor.post("/retirar-do-credor", headers=h).json()

    assert cliente["enviado_ao_credor"] is False and cliente["consentimento_ativo"] is True
    assert analista.get(f"/solicitacoes/{sid}").json()["status"] == "revogado"
    assert consumidor.get("/meu-score", headers=h).status_code == 200  # o score dele continua
    assert consumidor.post("/retirar-do-credor", headers=h).status_code == 409

    assert consumidor.post("/enviar-ao-credor", headers=h).status_code == 200
    assert len(analista.get("/solicitacoes").json()) == 2


def test_trocar_telefone_retira_tambem_o_pedido_do_credor(mundo):
    operadora, consumidor, analista = mundo
    _, h = _com_score(operadora, consumidor, "maria")
    consumidor.post("/enviar-ao-credor", headers=h).raise_for_status()
    sid = analista.get("/solicitacoes").json()[0]["id"]

    r = consumidor.patch("/meus-dados", json={"telefone": "11900000000"}, headers=h)

    assert r.status_code == 200, r.text
    assert r.json()["enviado_ao_credor"] is False and r.json()["consentimento_ativo"] is False
    assert analista.get(f"/solicitacoes/{sid}").json()["status"] == "revogado"


def test_chave_de_servico_errada_vira_502_sem_deixar_consentimento_solto(credor):
    operadora = TestClient(criar_operadora(tamanho_populacao=50, semente=1, demo=True))
    analista = credor(db_url="sqlite://", operadora_url="http://operadora", transporte=_Ponte(operadora))
    consumidor = TestClient(
        criar_consumidor(
            db_url="sqlite://",
            operadora_url="http://operadora",
            transporte=_Ponte(operadora),
            credor_url="http://credor",
            transporte_credor=_Ponte(TestClient(analista.app)),
            chave_servico="chave-errada",
            segredo="segredo-de-teste-com-32-bytes-ou-mais!!",
        )
    )
    _, h = _com_score(operadora, consumidor, "maria")

    r = consumidor.post("/enviar-ao-credor", headers=h)

    assert r.status_code == 502
    assert analista.get("/solicitacoes").json() == []
    assert consumidor.get("/me", headers=h).json()["enviado_ao_credor"] is False
    assert consumidor.post("/enviar-ao-credor", headers=h).status_code == 502  # pode tentar de novo
