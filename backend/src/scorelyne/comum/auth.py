"""Autenticação com JWT e papéis.

Cada serviço tem o seu próprio `Autenticador` (segredo e papel próprios): um token emitido pelo
consumidor não vale no credor, e vice-versa. Senhas usam scrypt da biblioteca padrão.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .erros import ErroApi

_N, _R, _P = 2**14, 8, 1
bearer = HTTPBearer(auto_error=False)


def hash_senha(senha: str) -> str:
    sal = os.urandom(16)
    h = hashlib.scrypt(senha.encode(), salt=sal, n=_N, r=_R, p=_P)
    return f"scrypt${sal.hex()}${h.hex()}"


def senha_confere(senha: str, armazenado: str) -> bool:
    try:
        _, sal, h = armazenado.split("$")
        calculado = hashlib.scrypt(senha.encode(), salt=bytes.fromhex(sal), n=_N, r=_R, p=_P)
    except ValueError:
        return False
    return hmac.compare_digest(calculado.hex(), h)


def chave_valida(recebida: str | None, esperada: str | None) -> bool:
    """Compara chaves de serviço em tempo constante. Sem chave configurada, nada passa."""
    if not recebida or not esperada:
        return False
    return hmac.compare_digest(recebida.encode(), esperada.encode())


class Autenticador:
    """Emite e valida tokens de um único papel (`consumidor` ou `analista`)."""

    def __init__(self, papel: str, segredo: str | None = None, validade_min: int = 60):
        self.papel = papel
        # Sem segredo configurado, vale um aleatório por processo: os tokens caem ao reiniciar.
        self.segredo = segredo or secrets.token_hex(32)
        self.validade = timedelta(minutes=validade_min)

    def criar_token(self, sujeito: str) -> str:
        agora = datetime.now(UTC)
        corpo = {"sub": sujeito, "papel": self.papel, "iat": agora, "exp": agora + self.validade}
        return jwt.encode(corpo, self.segredo, algorithm="HS256")

    def _ler(self, token: str) -> str:
        try:
            corpo = jwt.decode(token, self.segredo, algorithms=["HS256"], options={"require": ["exp", "sub"]})
        except jwt.PyJWTError as exc:
            raise ErroApi(401, "Token inválido ou expirado") from exc
        if corpo.get("papel") != self.papel:
            raise ErroApi(403, "Este token não tem permissão para este serviço")
        return corpo["sub"]

    def sujeito(self, credencial: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> str:
        """Dependência FastAPI: devolve o id de quem está logado ou barra a requisição."""
        if credencial is None:
            raise ErroApi(401, "Faça login para continuar")
        return self._ler(credencial.credentials)
