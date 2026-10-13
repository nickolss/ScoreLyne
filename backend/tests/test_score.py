from itertools import combinations

import pytest

from scorelyne.operadora.generator import gerar_populacao
from scorelyne.operadora.models import Escopo
from scorelyne.operadora.personas import gerar_personas
from scorelyne.operadora.store import montar_dados
from scorelyne.score import politica
from scorelyne.score.analise import EscoposObrigatoriosAusentes, analisar
from scorelyne.score.fatores import StatusFator, calcular_fatores
from scorelyne.score.modelo import carregar_modelo

TODOS = list(Escopo)
OPCIONAIS = [e for e in Escopo if e not in politica.ESCOPOS_OBRIGATORIOS]


def dados(chave, escopos=TODOS):
    return montar_dados(gerar_personas()[chave], escopos, "teste")


def test_pos_pago_nao_tem_regularidade_de_recarga():
    fatores = {f.chave: f for f in calcular_fatores(dados("carlos"))}
    assert fatores[Escopo.RECARGAS].status is StatusFator.NAO_SE_APLICA
    assert "6 das últimas 12" in fatores[Escopo.PONTUALIDADE].evidencia


def test_pontos_somam_o_score():
    r = analisar(dados("maria"), 1500)
    assert round(r.pontos_base + sum(f.pontos for f in r.fatores)) == r.score


def test_modelo_nunca_premia_comportamento_pior():
    assert all(w <= 0 for w in carregar_modelo().coeficientes.values())


@pytest.mark.parametrize(
    ("chave", "esperado"),
    [
        ("maria", politica.Decisao.APROVADO),
        ("joao", politica.Decisao.APROVADO),
        ("carlos", politica.Decisao.RECUSADO),
        ("luciana", politica.Decisao.REVISAO),
    ],
)
def test_decisao_das_personas(chave, esperado):
    assert analisar(dados(chave)).decisao is esperado


def test_historico_curto_nunca_e_decidido_sozinho():
    r = analisar(dados("luciana"))
    assert r.confianca is politica.Confianca.BAIXA
    assert any("Histórico curto" in m for m in r.motivos_revisao)


def test_recusa_vem_com_plano_de_melhora_e_sem_oferta():
    r = analisar(dados("carlos"), 5000)
    assert r.oferta is None
    assert r.plano_de_melhora


def test_oferta_nunca_passa_do_pedido():
    r = analisar(dados("maria"), 1500)
    assert r.oferta.valor_ofertado == 1500


def test_escopo_obrigatorio_ausente_e_recusado():
    with pytest.raises(EscoposObrigatoriosAusentes):
        analisar(dados("carlos", [e for e in Escopo if e is not Escopo.PONTUALIDADE]))


def test_omitir_escopo_opcional_nunca_aumenta_o_score():
    linhas = list(gerar_personas().values()) + [l for l, _ in gerar_populacao(300, semente=3)]
    for linha in linhas:
        completo = analisar(montar_dados(linha, TODOS, "t")).score
        for n in range(1, len(OPCIONAIS) + 1):
            for omitidos in combinations(OPCIONAIS, n):
                escopos = [e for e in Escopo if e not in omitidos]
                assert analisar(montar_dados(linha, escopos, "t")).score <= completo
