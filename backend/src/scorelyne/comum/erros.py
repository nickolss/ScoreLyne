"""Erro de domínio que as APIs traduzem em resposta HTTP."""

from __future__ import annotations


class ErroApi(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem
