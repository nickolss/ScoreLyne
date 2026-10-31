import pytest
from fastapi.testclient import TestClient

from scorelyne.banco import servico
from scorelyne.banco.api import create_app

SEGREDO = "segredo-do-credor-com-32-bytes-ou-mais!"
CHAVE_SERVICO = "chave-de-servico-de-teste"
CHAVE_AGENTE = "chave-do-agente-de-teste"
SENHA_ANALISTA = "senha-forte-123"


@pytest.fixture
def credor():
    """Fábrica do app do credor. Devolve um cliente já com token de analista e chave de serviço."""

    def criar(**kwargs) -> TestClient:
        app = create_app(segredo=SEGREDO, chave_servico=CHAVE_SERVICO, chave_agente=CHAVE_AGENTE, **kwargs)
        with app.state.sessoes() as s:
            analista = servico.criar_analista(s, "ana@teste.com", "Ana Analista", SENHA_ANALISTA)
        token = app.state.auth.criar_token(analista.id)
        return TestClient(app, headers={"Authorization": f"Bearer {token}", "X-Service-Key": CHAVE_SERVICO})

    return criar
