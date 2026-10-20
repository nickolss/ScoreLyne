"""Regras do lado do banco: criar solicitação, decidir, desfazer e revogar.

Toda mudança de estado gera um evento na trilha de auditoria.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from scorelyne.comum.analise import analisar_com_tratamento
from scorelyne.comum.auth import hash_senha, senha_confere
from scorelyne.comum.erros import ErroApi
from scorelyne.comum.operadora import Operadora
from scorelyne.score import politica
from scorelyne.score.analise import ResultadoAnalise

from .db import AnalistaDB, EventoDB, SolicitacaoDB, agora
from .esquemas import (
    DecisaoAnalista,
    Evento,
    LoginAnalista,
    NovaSolicitacao,
    RevisaoHumana,
    SituacaoSolicitacao,
    Solicitacao,
    SolicitacaoResumo,
    Status,
    Veredito,
)

ROTULO_DECISAO = {
    politica.Decisao.APROVADO: "Pré-aprovação automática",
    politica.Decisao.REVISAO: "Encaminhado a um analista",
    politica.Decisao.RECUSADO: "Recusa com plano de melhora enviado ao cliente",
}


ErroBanco = ErroApi
__all__ = ["ErroBanco", "Operadora", "analisar_com_tratamento"]


def _evento(s: SolicitacaoDB, ator: str, tipo: str, titulo: str, detalhe: str | None = None) -> None:
    s.eventos.append(EventoDB(ator=ator, tipo=tipo, titulo=titulo, detalhe=detalhe))


def _status(s: SolicitacaoDB) -> Status:
    if s.revogado_em:
        return Status.REVOGADO
    if s.decisao_final:
        return Status(s.decisao_final)
    return Status(s.decisao_agente)


def resumo(s: SolicitacaoDB) -> SolicitacaoResumo:
    return SolicitacaoResumo(
        id=s.id,
        criado_em=s.criado_em,
        nome=s.nome,
        ocupacao=s.ocupacao,
        plano=s.plano,
        valor_solicitado=s.valor_solicitado,
        score=s.score,
        decisao_agente=politica.Decisao(s.decisao_agente),
        status=_status(s),
    )


def completa(s: SolicitacaoDB) -> Solicitacao:
    revisao = None
    if s.decisao_final:
        revisao = RevisaoHumana(
            veredito=Veredito.APROVAR if s.decisao_final == Status.APROVADO else Veredito.RECUSAR,
            justificativa=s.justificativa,
            analista=s.analista,
            em=s.decidido_em,
        )
    return Solicitacao(
        **resumo(s).model_dump(),
        atualizado_em=s.atualizado_em,
        telefone=s.telefone,
        cidade=s.cidade,
        uf=s.uf,
        finalidade=s.finalidade,
        consentimento_id=s.consentimento_id,
        escopos=s.escopos,
        analise=ResultadoAnalise.model_validate(s.analise) if s.analise else None,
        revisao_humana=revisao,
        revogado_em=s.revogado_em,
        eventos=[
            Evento(em=e.em, ator=e.ator, tipo=e.tipo, titulo=e.titulo, detalhe=e.detalhe) for e in s.eventos
        ],
    )


def situacao(s: SolicitacaoDB) -> SituacaoSolicitacao:
    c = completa(s)
    return SituacaoSolicitacao(
        id=c.id,
        status=c.status,
        decisao_agente=c.decisao_agente,
        score=c.score,
        oferta=c.analise.oferta if c.analise else None,
        motivos_revisao=c.analise.motivos_revisao if c.analise else [],
        revisao_humana=c.revisao_humana,
        atualizado_em=c.atualizado_em,
    )


def criar(sessao: Session, operadora: Operadora, pedido: NovaSolicitacao) -> SolicitacaoDB:
    dados = operadora.dados(pedido.telefone, pedido.consentimento_id)
    consentimento = operadora.consentimento(pedido.consentimento_id)
    resultado = analisar_com_tratamento(dados, pedido.valor_solicitado)

    s = SolicitacaoDB(
        id=str(uuid.uuid4()),
        nome=pedido.nome,
        telefone=pedido.telefone,
        ocupacao=pedido.ocupacao,
        cidade=pedido.cidade,
        uf=pedido.uf,
        valor_solicitado=pedido.valor_solicitado,
        finalidade=pedido.finalidade,
        consentimento_id=pedido.consentimento_id,
        escopos=[e.value for e in dados.escopos],
        plano=dados.permanencia.plano_atual.value if dados.permanencia else None,
        score=resultado.score,
        decisao_agente=resultado.decisao.value,
        analise=resultado.model_dump(mode="json"),
    )
    validade = consentimento["expira_em"][:10]
    _evento(
        s,
        "cliente",
        "consentimento",
        "Consentimento registrado na operadora",
        f"Finalidade: {consentimento['finalidade'].replace('_', ' ')} · {len(dados.escopos)} categorias · válido até {validade}",
    )
    _evento(
        s,
        "agente",
        "dados_recebidos",
        "Dados recebidos da operadora",
        "Só os blocos autorizados, sem nome, CPF ou localização: "
        + ", ".join(e.value for e in dados.escopos),
    )
    _evento(
        s,
        "agente",
        "score",
        "Score calculado",
        f"{resultado.score} pontos · probabilidade de inadimplência {resultado.probabilidade_inadimplencia:.1%}"
        f" · modelo {resultado.modelo_versao}",
    )
    _evento(
        s,
        "agente",
        "equidade",
        "Checagem de variáveis",
        "O modelo usa só os 5 fatores de comportamento; região, idade e gênero não entram",
    )
    detalhe = "; ".join(resultado.motivos_revisao) if resultado.motivos_revisao else None
    _evento(s, "agente", "decisao_agente", ROTULO_DECISAO[resultado.decisao], detalhe)

    sessao.add(s)
    sessao.commit()
    return s


def obter(sessao: Session, solicitacao_id: str) -> SolicitacaoDB:
    s = sessao.get(SolicitacaoDB, solicitacao_id)
    if s is None:
        raise ErroBanco(404, "Solicitação não encontrada")
    return s


def listar(sessao: Session, status: Status | None = None) -> list[SolicitacaoDB]:
    todas = sessao.scalars(select(SolicitacaoDB).order_by(SolicitacaoDB.criado_em.desc())).all()
    return [s for s in todas if status is None or _status(s) is status]


def decidir(sessao: Session, solicitacao_id: str, decisao: DecisaoAnalista, analista: str) -> SolicitacaoDB:
    s = obter(sessao, solicitacao_id)
    if s.revogado_em:
        raise ErroBanco(409, "Consentimento revogado: a solicitação não pode mais ser decidida")
    s.decisao_final = Status.APROVADO.value if decisao.veredito is Veredito.APROVAR else Status.RECUSADO.value
    s.justificativa = decisao.justificativa
    s.analista = analista
    s.decidido_em = agora()
    sobrepoe = s.decisao_agente != politica.Decisao.REVISAO and s.decisao_final != s.decisao_agente
    titulo = (
        "Crédito aprovado pelo analista"
        if s.decisao_final == "aprovado"
        else "Crédito recusado pelo analista"
    )
    if sobrepoe:
        titulo += " (sobrepondo o agente)"
    _evento(s, "analista", "decisao_analista", titulo, f"{analista}: “{decisao.justificativa}”")
    sessao.commit()
    return s


def desfazer(sessao: Session, solicitacao_id: str) -> SolicitacaoDB:
    s = obter(sessao, solicitacao_id)
    if not s.decisao_final:
        raise ErroBanco(409, "Não há decisão do analista para desfazer")
    _evento(s, "analista", "decisao_desfeita", "Decisão do analista desfeita", s.analista)
    s.decisao_final = s.justificativa = s.analista = s.decidido_em = None
    sessao.commit()
    return s


def revogar(sessao: Session, operadora: Operadora, solicitacao_id: str) -> SolicitacaoDB:
    """Revoga na operadora e apaga a análise. Fica só o registro de que ela existiu."""
    s = obter(sessao, solicitacao_id)
    if s.revogado_em:
        return s
    operadora.revogar(s.consentimento_id)
    s.revogado_em = agora()
    s.analise = None
    s.score = None
    _evento(
        s,
        "cliente",
        "consentimento_revogado",
        "Consentimento revogado pelo cliente",
        "Dados telecom e score apagados; a operadora bloqueia novos acessos",
    )
    sessao.commit()
    return s


def criar_analista(sessao: Session, email: str, nome: str, senha: str) -> AnalistaDB:
    a = AnalistaDB(id=str(uuid.uuid4()), email=email.lower(), nome=nome, senha_hash=hash_senha(senha))
    sessao.add(a)
    sessao.commit()
    return a


def autenticar_analista(sessao: Session, login: LoginAnalista) -> AnalistaDB:
    a = sessao.scalar(select(AnalistaDB).where(AnalistaDB.email == login.email.lower()))
    # Mesma resposta para e-mail desconhecido e senha errada.
    if a is None or not senha_confere(login.senha, a.senha_hash):
        raise ErroBanco(401, "E-mail ou senha incorretos")
    return a


def obter_analista(sessao: Session, analista_id: str) -> AnalistaDB:
    a = sessao.get(AnalistaDB, analista_id)
    if a is None:
        raise ErroBanco(401, "Analista não encontrado")
    return a
