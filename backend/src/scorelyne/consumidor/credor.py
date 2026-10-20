"""Cliente HTTP do módulo do credor, autenticado com a chave de serviço (X-Service-Key).

O consumidor só usa três chamadas: criar a solicitação, ver a situação dela e revogar. Nenhuma lê a fila
do credor nem os dados de outras pessoas.
"""

from __future__ import annotations

import httpx

from scorelyne.comum.erros import ErroApi

# Erros do credor que o consumidor repassa como estão. O resto (chave errada, falha interna) vira 502,
# porque não é algo que a pessoa possa corrigir.
REPASSADOS = {404, 409, 422}


class Credor:
    def __init__(self, cliente: httpx.Client):
        self.cliente = cliente

    def _chamar(self, metodo: str, caminho: str, **kwargs) -> dict:
        try:
            r = self.cliente.request(metodo, caminho, **kwargs)
        except httpx.HTTPError as exc:
            raise ErroApi(503, "O credor está indisponível no momento") from exc
        if r.status_code >= 400:
            try:
                detalhe = r.json().get("detail", "erro")
            except ValueError:
                detalhe = "erro"
            if r.status_code in REPASSADOS:
                raise ErroApi(r.status_code, f"Credor: {detalhe}")
            raise ErroApi(502, "O credor recusou a comunicação. Tente novamente mais tarde.")
        return r.json()

    def criar(self, pedido: dict) -> dict:
        return self._chamar("POST", "/solicitacoes", json=pedido)

    def situacao(self, solicitacao_id: str) -> dict:
        return self._chamar("GET", f"/solicitacoes/{solicitacao_id}/situacao")

    def revogar(self, solicitacao_id: str) -> dict:
        return self._chamar("POST", f"/solicitacoes/{solicitacao_id}/revogar")
