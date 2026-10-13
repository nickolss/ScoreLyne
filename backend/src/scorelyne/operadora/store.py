"""Base em memória da operadora: linhas, consentimentos e trilha de acessos."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from .generator import DATA_REFERENCIA, competencia, gerar_populacao, meses_entre
from .models import (
    Acesso,
    Consentimento,
    ConsentimentoEntrada,
    DadosConsistencia,
    DadosEstabilidade,
    DadosLinha,
    DadosPermanencia,
    DadosPontualidade,
    DadosRecargas,
    Escopo,
    FaturaPagamento,
    Linha,
    PerfilOculto,
    ValorMensal,
)
from .personas import gerar_personas


class ErroConsentimento(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


class Base:
    def __init__(self, tamanho_populacao: int = 3000, semente: int = 42):
        self.personas = gerar_personas()
        self.linhas: dict[str, Linha] = {p.telefone: p for p in self.personas.values()}
        self.perfis: dict[str, PerfilOculto] = {}
        for linha, perfil in gerar_populacao(tamanho_populacao, semente, reservados=set(self.linhas)):
            self.linhas[linha.telefone] = linha
            self.perfis[linha.telefone] = perfil
        self.consentimentos: dict[str, Consentimento] = {}

    # --- Consentimento ---------------------------------------------------------

    def criar_consentimento(self, entrada: ConsentimentoEntrada) -> Consentimento:
        linha = self.linhas.get(entrada.telefone)
        if linha is None:
            raise ErroConsentimento(404, "Linha não encontrada nesta operadora")
        if linha.cpf != entrada.cpf:
            raise ErroConsentimento(403, "CPF não confere com o titular da linha")
        agora = datetime.now(UTC)
        consentimento = Consentimento(
            id=str(uuid.uuid4()),
            telefone=entrada.telefone,
            escopos=sorted(set(entrada.escopos)),
            finalidade=entrada.finalidade,
            solicitante=entrada.solicitante,
            criado_em=agora,
            expira_em=agora + timedelta(days=entrada.validade_dias),
        )
        self.consentimentos[consentimento.id] = consentimento
        return consentimento

    def obter_consentimento(self, consentimento_id: str) -> Consentimento:
        consentimento = self.consentimentos.get(consentimento_id)
        if consentimento is None:
            raise ErroConsentimento(404, "Consentimento não encontrado")
        return consentimento

    def revogar_consentimento(self, consentimento_id: str) -> Consentimento:
        consentimento = self.obter_consentimento(consentimento_id)
        if consentimento.revogado_em is None:
            consentimento.revogado_em = datetime.now(UTC)
        return consentimento

    def _validar(self, consentimento_id: str, telefone: str) -> Consentimento:
        consentimento = self.consentimentos.get(consentimento_id)
        if consentimento is None:
            raise ErroConsentimento(403, "Consentimento inexistente")
        if consentimento.telefone != telefone:
            raise ErroConsentimento(403, "Consentimento não cobre esta linha")
        if consentimento.revogado_em is not None:
            raise ErroConsentimento(403, "Consentimento revogado pelo titular")
        if consentimento.expira_em < datetime.now(UTC):
            raise ErroConsentimento(403, "Consentimento expirado")
        return consentimento

    # --- Dados -----------------------------------------------------------------

    def dados(self, telefone: str, consentimento_id: str) -> DadosLinha:
        linha = self.linhas.get(telefone)
        if linha is None:
            raise ErroConsentimento(404, "Linha não encontrada nesta operadora")
        consentimento = self._validar(consentimento_id, telefone)
        consentimento.acessos.append(Acesso(em=datetime.now(UTC), escopos=consentimento.escopos))
        return montar_dados(linha, consentimento.escopos, consentimento.id)


def montar_dados(linha: Linha, escopos: list[Escopo], consentimento_id: str) -> DadosLinha:
    """Visão da linha que a operadora entrega ao banco: só os blocos dos escopos autorizados."""
    autorizados = set(escopos)
    resposta = DadosLinha(
        telefone=linha.telefone,
        consentimento_id=consentimento_id,
        data_referencia=DATA_REFERENCIA,
        escopos=sorted(autorizados),
    )
    if Escopo.PERMANENCIA in autorizados:
        resposta.permanencia = DadosPermanencia(
            ativada_em=linha.ativada_em,
            meses_na_base=meses_entre(linha.ativada_em, DATA_REFERENCIA),
            plano_atual=linha.plano,
            veio_por_portabilidade=linha.portabilidade_entrada is not None,
            mudancas_plano=linha.mudancas_plano,
        )
    if Escopo.RECARGAS in autorizados:
        resposta.recargas = DadosRecargas(datas=[r.data for r in linha.recargas])
    if Escopo.PONTUALIDADE in autorizados:
        resposta.pontualidade = DadosPontualidade(
            faturas=[
                FaturaPagamento(competencia=f.competencia, vencimento=f.vencimento, pago_em=f.pago_em)
                for f in linha.faturas
            ],
            saldos_zerados=linha.saldos_zerados,
            suspensoes=linha.suspensoes,
        )
    if Escopo.ESTABILIDADE in autorizados:
        resposta.estabilidade = DadosEstabilidade(
            trocas_chip=linha.trocas_chip,
            portabilidade_entrada=linha.portabilidade_entrada,
        )
    if Escopo.CONSISTENCIA in autorizados:
        resposta.consistencia = DadosConsistencia(valores_mensais=_valores_mensais(linha))
    return resposta


def _valores_mensais(linha: Linha) -> list[ValorMensal]:
    recargas: dict[str, float] = defaultdict(float)
    for r in linha.recargas:
        recargas[competencia(r.data)] += r.valor
    # Fatura agregada pelo mês de vencimento, que é quando o cliente sente o gasto.
    faturas = {competencia(f.vencimento): f.valor for f in linha.faturas}
    meses = sorted(set(recargas) | set(faturas))
    return [
        ValorMensal(competencia=m, total_recargas=round(recargas.get(m, 0.0), 2), valor_fatura=faturas.get(m))
        for m in meses
    ]
