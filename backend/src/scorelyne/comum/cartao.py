"""Cartão público do modelo: pesos, limiares, métricas e equidade.

É o mesmo para quem consulta pelo módulo do consumidor e pelo do credor, então mora em `comum`.
"""

from __future__ import annotations

from pydantic import BaseModel

from scorelyne.operadora.models import Escopo
from scorelyne.score import politica
from scorelyne.score.fatores import ROTULOS
from scorelyne.score.modelo import Escala, carregar_modelo


class FatorModelo(BaseModel):
    chave: Escopo
    rotulo: str
    importancia: float
    obrigatorio: bool
    ativo: bool
    perda_maxima_se_omitir: int  # pontos que o score pode cair se o titular não autorizar


class CartaoModelo(BaseModel):
    """Resumo público do modelo, para a página de governança e para auditoria."""

    versao: str
    fatores: list[FatorModelo]
    limiares: dict[str, int]
    escala: Escala
    metricas: dict[str, float]
    equidade: dict


def cartao_modelo() -> CartaoModelo:
    m = carregar_modelo()
    return CartaoModelo(
        versao=m.versao,
        fatores=[
            FatorModelo(
                chave=k,
                rotulo=ROTULOS[k],
                importancia=m.importancia[k],
                obrigatorio=k in politica.ESCOPOS_OBRIGATORIOS,
                ativo=m.coeficientes[k] != 0,
                perda_maxima_se_omitir=round(
                    m.escala.fator * abs(m.coeficientes[k]) * (100 - m.conservador[k]) / 100
                ),
            )
            for k in ROTULOS
        ],
        limiares={"aprovacao": politica.LIMIAR_APROVACAO, "revisao": politica.LIMIAR_REVISAO},
        escala=m.escala,
        metricas=m.metricas,
        equidade=m.equidade,
    )
