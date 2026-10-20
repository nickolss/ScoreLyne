"""Roda o motor de score traduzindo as falhas de regra em erro HTTP 422."""

from __future__ import annotations

from scorelyne.operadora.models import DadosLinha
from scorelyne.score.analise import EscoposObrigatoriosAusentes, ResultadoAnalise, analisar
from scorelyne.score.fatores import HistoricoInsuficiente

from .erros import ErroApi


def analisar_com_tratamento(dados: DadosLinha, valor: float | None) -> ResultadoAnalise:
    try:
        return analisar(dados, valor)
    except (EscoposObrigatoriosAusentes, HistoricoInsuficiente) as exc:
        raise ErroApi(422, str(exc)) from exc
