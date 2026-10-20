"""Cliente HTTP da operadora mock, usado pelos dois serviços."""

from __future__ import annotations

import httpx

from scorelyne.operadora.models import DadosLinha

from .erros import ErroApi


class Operadora:
    def __init__(self, cliente: httpx.Client):
        self.cliente = cliente

    def _chamar(self, metodo: str, caminho: str, **kwargs) -> dict:
        try:
            r = self.cliente.request(metodo, caminho, **kwargs)
        except httpx.HTTPError as exc:
            raise ErroApi(503, "Operadora indisponível no momento") from exc
        if r.status_code >= 400:
            raise ErroApi(r.status_code, f"Operadora: {r.json().get('detail', 'erro')}")
        return r.json()

    def criar_consentimento(self, corpo: dict) -> dict:
        return self._chamar("POST", "/consentimentos", json=corpo)

    def dados(self, telefone: str, consentimento_id: str) -> DadosLinha:
        resposta = self._chamar(
            "GET", f"/linhas/{telefone}/dados", headers={"X-Consentimento-Id": consentimento_id}
        )
        return DadosLinha.model_validate(resposta)

    def consentimento(self, consentimento_id: str) -> dict:
        return self._chamar("GET", f"/consentimentos/{consentimento_id}")

    def revogar(self, consentimento_id: str) -> dict:
        return self._chamar("DELETE", f"/consentimentos/{consentimento_id}")
