"""O registro de fórmulas (formulas.yaml) não pode divergir do que o código calcula."""

import math

import pytest
from fastapi.testclient import TestClient

from scorelyne.consumidor.api import create_app as criar_consumidor
from scorelyne.operadora.models import Escopo
from scorelyne.operadora.personas import maria
from scorelyne.operadora.store import montar_dados
from scorelyne.score import fatores, politica
from scorelyne.score.analise import analisar
from scorelyne.score.fatores import ROTULOS, _nota_fatura
from scorelyne.score.formulas import carregar_formulas
from scorelyne.score.modelo import Escala

F = carregar_formulas()


def test_registro_cobre_os_cinco_fatores_com_o_mesmo_rotulo_do_codigo():
    assert [f.id for f in F.fatores] == list(ROTULOS)
    for f in F.fatores:
        assert f.rotulo == ROTULOS[f.id]
        assert f.formula and f.versao


def test_janela_do_registro_e_a_do_codigo():
    for f in F.fatores:
        if "janela_meses" in f.parametros:
            assert f.parametros["janela_meses"] == fatores.JANELA_MESES, f.id


def test_notas_de_fatura_por_atraso_batem_com_o_codigo():
    p = F.fator(Escopo.PONTUALIDADE).parametros
    assert _nota_fatura(None) == p["nota_fatura_em_aberto"]
    for faixa in p["nota_fatura_por_atraso_em_dias"]:
        if "ate_dias" in faixa:
            assert _nota_fatura(faixa["ate_dias"]) == faixa["nota"], faixa
        else:
            assert _nota_fatura(faixa["acima_de_dias"] + 1) == faixa["nota"], faixa


def test_permanencia_satura_na_referencia_do_registro():
    ref = F.fator(Escopo.PERMANENCIA).parametros["meses_de_referencia"]
    assert round(100 * min(1.0, math.log1p(ref) / math.log1p(120)), 1) == 100.0


def test_politica_do_registro_e_a_do_codigo():
    p = F.politica.parametros
    assert p["limiar_aprovacao"] == politica.LIMIAR_APROVACAO
    assert p["limiar_revisao"] == politica.LIMIAR_REVISAO
    assert p["meses_minimos_para_confianca_alta"] == politica.MESES_MINIMOS
    assert p["fatores_minimos_para_confianca_alta"] == politica.FATORES_MINIMOS
    assert p["limite_maximo"] == politica.LIMITE_MAXIMO
    assert tuple(p["prazos_meses"]) == politica.PRAZOS


def test_escala_do_registro_e_a_do_codigo():
    p = F.modelo.parametros
    assert p["pd_aprovacao"] == Escala().pd_aprovacao
    assert p["pd_revisao"] == Escala().pd_revisao


@pytest.mark.parametrize("score", [550, 650, 750, 900])
def test_formulas_de_oferta_batem_com_o_texto_do_registro(score):
    # limite = mínimo(4000, arredondar((score − 500) ÷ 500 × 40) × 100)
    esperado = min(4000, round((score - 500) / 500 * 40) * 100)
    assert politica.limite_sugerido(score) == esperado
    # taxa = máximo(1,9; 5,5 − (score − 550) × 0,009)
    assert politica.taxa_mensal(score) == round(max(1.9, 5.5 - (score - 550) * 0.009), 2)


def test_analise_grava_a_versao_do_registro_e_de_cada_fator():
    dados = montar_dados(maria(), list(Escopo), "teste")
    r = analisar(dados, 1000)
    assert r.formulas_versao == F.versao
    assert {f.chave: f.formula_versao for f in r.fatores} == {f.id: f.versao for f in F.fatores}


def test_endpoint_publico_de_formulas_do_consumidor():
    app = criar_consumidor(db_url="sqlite://", segredo="x" * 40)
    r = TestClient(app).get("/formulas")
    assert r.status_code == 200
    assert r.json()["versao"] == F.versao
    assert len(r.json()["fatores"]) == 5
    modelo = TestClient(app).get("/modelo")  # o consumidor vê o cartão do modelo sem passar pelo credor
    assert modelo.status_code == 200
    assert {f["chave"] for f in modelo.json()["fatores"]} == {f.id.value for f in F.fatores}
