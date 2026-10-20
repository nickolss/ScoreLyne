"""Modelo de risco: regressão logística sobre os cinco fatores, em escala de scorecard.

Por ser linear, a contribuição de cada fator é exata e aditiva (antes do corte em 0–1000):
    score = pontos_base + Σ pontos_fator
onde pontos_fator = -B · w · (x - média). É o mesmo valor que o SHAP (LinearExplainer)
daria em log-odds, convertido para pontos de score.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from scorelyne.operadora.models import Escopo

from . import politica
from .fatores import ORDEM, Fator, StatusFator

ARQUIVO_MODELO = Path(__file__).with_name("modelo.json")


class Escala(BaseModel):
    """Liga o score ao apetite de risco: o limiar de aprovação corresponde a `pd_aprovacao`
    e o de revisão a `pd_revisao`. Entre eles, o score é linear no log das chances."""

    pd_aprovacao: float = 0.10
    pd_revisao: float = 0.25

    @staticmethod
    def _log_odds_bom(pd: float) -> float:
        return math.log((1 - pd) / pd)

    @property
    def fator(self) -> float:
        """Pontos de score por unidade de log-odds."""
        amplitude = politica.LIMIAR_APROVACAO - politica.LIMIAR_REVISAO
        return amplitude / (self._log_odds_bom(self.pd_aprovacao) - self._log_odds_bom(self.pd_revisao))

    def pontos(self, log_odds_bom: float) -> float:
        return politica.LIMIAR_APROVACAO + self.fator * (log_odds_bom - self._log_odds_bom(self.pd_aprovacao))


class Modelo(BaseModel):
    versao: str
    treinado_em: datetime
    intercepto: float
    coeficientes: dict[Escopo, float]
    medias: dict[Escopo, float]  # usadas quando o fator não se aplica (efeito neutro)
    conservador: dict[Escopo, float]  # usado quando o titular não autoriza (sem dado, sem benefício)
    importancia: dict[Escopo, float]
    escala: Escala = Escala()
    metricas: dict[str, float] = {}
    equidade: dict = {}


class Contribuicao(BaseModel):
    chave: Escopo
    valor_usado: float  # 0–100, depois de imputação
    pontos: float


class Pontuacao(BaseModel):
    score: int
    probabilidade_inadimplencia: float
    pontos_base: float
    contribuicoes: list[Contribuicao]


def valor_para_modelo(fator: Fator, modelo: Modelo) -> float:
    if fator.status is StatusFator.CALCULADO:
        return fator.valor
    if fator.status is StatusFator.NAO_SE_APLICA:
        return modelo.medias[fator.chave]
    return modelo.conservador[fator.chave]


def pontuar(fatores: list[Fator], modelo: Modelo) -> Pontuacao:
    por_chave = {f.chave: f for f in fatores}
    b = modelo.escala.fator
    logit_medio = modelo.intercepto + sum(modelo.coeficientes[k] * modelo.medias[k] / 100 for k in ORDEM)
    pontos_base = modelo.escala.pontos(-logit_medio)

    contribuicoes, logit = [], modelo.intercepto
    for k in ORDEM:
        x = valor_para_modelo(por_chave[k], modelo)
        w = modelo.coeficientes[k]
        logit += w * x / 100
        contribuicoes.append(
            Contribuicao(
                chave=k, valor_usado=round(x, 1), pontos=round(-b * w * (x - modelo.medias[k]) / 100, 1)
            )
        )

    bruto = pontos_base + sum(c.pontos for c in contribuicoes)
    return Pontuacao(
        score=max(0, min(1000, round(bruto))),
        probabilidade_inadimplencia=round(1 / (1 + math.exp(-logit)), 4),
        pontos_base=round(pontos_base, 1),
        contribuicoes=contribuicoes,
    )


@lru_cache(maxsize=1)
def carregar_modelo(caminho: Path = ARQUIVO_MODELO) -> Modelo:
    if not caminho.exists():
        raise FileNotFoundError(f"Modelo não encontrado em {caminho}. Rode `uv run score treinar`.")
    return Modelo.model_validate_json(caminho.read_text(encoding="utf-8"))


def salvar_modelo(modelo: Modelo, caminho: Path = ARQUIVO_MODELO, pasta_versoes: Path | None = None) -> None:
    """Grava o modelo vigente e guarda uma cópia em versoes/ para o histórico."""
    texto = json.dumps(modelo.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    caminho.write_text(texto, encoding="utf-8")
    pasta = pasta_versoes if pasta_versoes is not None else caminho.with_name("versoes")
    pasta.mkdir(exist_ok=True)
    (pasta / f"{modelo.versao}.json").write_text(texto, encoding="utf-8")
    carregar_modelo.cache_clear()


def nova_versao(semente: int) -> str:
    return f"{datetime.now(UTC):%Y%m%d}-s{semente}"
