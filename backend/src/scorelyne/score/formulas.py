"""Registro versionado das fórmulas do score (`formulas.yaml`).

O registro documenta o que o código calcula e ganha uma versão própria, gravada em cada análise
ao lado da versão do modelo. `tests/test_formulas.py` garante que os parâmetros do registro
batem com o código.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from scorelyne.operadora.models import Escopo

ARQUIVO_FORMULAS = Path(__file__).with_name("formulas.yaml")


class FormulaFator(BaseModel):
    id: Escopo
    rotulo: str
    versao: str
    formula: str
    entradas: list[str]
    parametros: dict[str, Any]
    observacao: str


class FormulaModelo(BaseModel):
    versao: str
    formula_score: str
    formula_pontos_fator: str
    formula_escala: str
    formula_probabilidade: str
    parametros: dict[str, Any]
    observacao: str


class FormulaPolitica(BaseModel):
    versao: str
    parametros: dict[str, Any]
    formulas: dict[str, str]
    regras_de_supervisao: list[str]


class RegistroFormulas(BaseModel):
    versao: str
    atualizado_em: date
    fatores: list[FormulaFator]
    modelo: FormulaModelo
    politica: FormulaPolitica

    def fator(self, chave: Escopo) -> FormulaFator:
        return next(f for f in self.fatores if f.id == chave)


@lru_cache(maxsize=1)
def carregar_formulas(caminho: Path = ARQUIVO_FORMULAS) -> RegistroFormulas:
    return RegistroFormulas.model_validate(yaml.safe_load(caminho.read_text(encoding="utf-8")))
