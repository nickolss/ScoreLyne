from datetime import timedelta

from scorelyne.operadora.generator import DATA_REFERENCIA, cpf_valido, gerar_populacao, meses_entre
from scorelyne.operadora.personas import gerar_personas


def test_populacao_e_deterministica():
    a = gerar_populacao(50, semente=7)
    b = gerar_populacao(50, semente=7)
    assert [x[0].model_dump() for x in a] == [x[0].model_dump() for x in b]


def test_eventos_ficam_entre_ativacao_e_referencia():
    for linha, _ in gerar_populacao(300, semente=1):
        datas = (
            [r.data for r in linha.recargas]
            + [f.vencimento for f in linha.faturas]
            + [s.data for s in linha.saldos_zerados]
            + linha.trocas_chip
        )
        assert all(linha.ativada_em <= d <= DATA_REFERENCIA for d in datas)
        assert cpf_valido(linha.cpf)


def test_taxa_de_inadimplencia_plausivel():
    pop = gerar_populacao(2000, semente=42)
    taxa = sum(p.inadimplente for _, p in pop) / len(pop)
    assert 0.10 < taxa < 0.30


def test_maria():
    maria = gerar_personas()["maria"]
    assert meses_entre(maria.ativada_em, DATA_REFERENCIA) == 74
    assert len(maria.recargas) == 71
    assert not maria.trocas_chip and maria.portabilidade_entrada is None
    assert {r.valor for r in maria.recargas} <= {20, 25, 30, 50}


def test_joao():
    joao = gerar_personas()["joao"]
    assert len(joao.faturas) == 38
    em_dia = [f for f in joao.faturas if f.pago_em and f.pago_em <= f.vencimento]
    assert len(em_dia) == 37
    assert [d.year for d in joao.trocas_chip] == [2025]


def test_ana():
    ana = gerar_personas()["ana"]
    assert meses_entre(ana.ativada_em, DATA_REFERENCIA) == 14
    assert len({(r.data.year, r.data.month) for r in ana.recargas}) == 10
    assert len(ana.saldos_zerados) == 5


def test_carlos():
    carlos = gerar_personas()["carlos"]
    assert meses_entre(carlos.ativada_em, DATA_REFERENCIA) == 112
    ultimas = carlos.faturas[-12:]
    atrasadas = [f for f in ultimas if f.pago_em and f.pago_em - f.vencimento > timedelta(days=15)]
    assert len(atrasadas) == 6
    assert len(carlos.suspensoes) == 2


def test_luciana():
    luciana = gerar_personas()["luciana"]
    assert meses_entre(luciana.ativada_em, DATA_REFERENCIA) == 5
    assert len(luciana.recargas) == 4


def test_cpfs_das_personas_sao_validos():
    assert all(cpf_valido(p.cpf) for p in gerar_personas().values())
