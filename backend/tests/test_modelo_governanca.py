"""Histórico de versões do modelo e calibração por grupo no cartão de governança."""

from scorelyne.score.modelo import ARQUIVO_MODELO, carregar_modelo, salvar_modelo


def test_salvar_modelo_guarda_copia_no_historico(tmp_path):
    modelo = carregar_modelo()
    caminho = tmp_path / "modelo.json"
    salvar_modelo(modelo, caminho)
    copia = tmp_path / "versoes" / f"{modelo.versao}.json"
    assert copia.exists()
    assert copia.read_text(encoding="utf-8") == caminho.read_text(encoding="utf-8")
    carregar_modelo.cache_clear()


def test_modelo_vigente_tem_copia_no_historico_do_repositorio():
    modelo = carregar_modelo()
    copia = ARQUIVO_MODELO.with_name("versoes") / f"{modelo.versao}.json"
    assert copia.exists(), "rode `uv run score treinar` e versione a pasta versoes/"
    assert copia.read_text(encoding="utf-8") == ARQUIVO_MODELO.read_text(encoding="utf-8")


def test_equidade_traz_calibracao_por_grupo():
    equidade = carregar_modelo().equidade
    assert set(equidade) == {"regiao", "plano"}
    for dimensao in equidade.values():
        for grupo in dimensao["grupos"].values():
            assert {"pd_prevista", "inadimplencia_real", "margem_95", "calibrado"} <= set(grupo)
        assert dimensao["calibrado_em_todos_os_grupos"] is True


def test_diferenca_de_aprovacao_por_plano_nao_e_erro_de_calibracao():
    """Documenta o achado: a regra 4/5 falha no plano, mas o modelo está calibrado em todos os planos.

    A diferença vem de risco e de informação distintos entre os planos (só o pré-pago tem o fator de
    recargas), não de um modelo que erra a probabilidade de um grupo. Se a calibração quebrar, este
    teste falha e a conversa de produto precisa recomeçar.
    """
    plano = carregar_modelo().equidade["plano"]
    assert plano["calibrado_em_todos_os_grupos"]
    assert not plano["passa_regra_4_5"]
