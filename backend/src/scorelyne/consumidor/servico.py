"""Regras do lado do consumidor: cadastro, consentimento e cálculo do próprio score."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scorelyne.comum.analise import analisar_com_tratamento
from scorelyne.comum.auth import hash_senha, senha_confere
from scorelyne.comum.erros import ErroApi
from scorelyne.comum.operadora import Operadora
from scorelyne.score.analise import ResultadoAnalise

from .db import ClienteDB, agora
from .esquemas import (
    AtualizarDados,
    Cadastro,
    Cliente,
    Login,
    MeuScore,
    PedidoConsentimento,
    PedidoScore,
)

SOLICITANTE = "ScoreLyne"
FINALIDADE_CONSENTIMENTO = "autoconsulta_de_score"


def publico(c: ClienteDB) -> Cliente:
    return Cliente(
        id=c.id,
        nome=c.nome,
        cpf=c.cpf,
        telefone=c.telefone,
        ocupacao=c.ocupacao,
        cidade=c.cidade,
        uf=c.uf,
        consentimento_ativo=c.consentimento_id is not None,
        escopos=c.escopos or [],
    )


def cadastrar(sessao: Session, dados: Cadastro) -> ClienteDB:
    c = ClienteDB(
        id=str(uuid.uuid4()),
        nome=dados.nome,
        cpf=dados.cpf,
        telefone=dados.telefone,
        senha_hash=hash_senha(dados.senha),
        ocupacao=dados.ocupacao,
        cidade=dados.cidade,
        uf=dados.uf,
    )
    sessao.add(c)
    try:
        sessao.commit()
    except IntegrityError as exc:
        sessao.rollback()
        raise ErroApi(409, "Já existe um cadastro com este CPF ou telefone") from exc
    return c


def autenticar(sessao: Session, login: Login) -> ClienteDB:
    c = sessao.scalar(select(ClienteDB).where(ClienteDB.cpf == login.cpf))
    # Mesma resposta para CPF desconhecido e senha errada: não revela quem tem cadastro.
    if c is None or not senha_confere(login.senha, c.senha_hash):
        raise ErroApi(401, "CPF ou senha incorretos")
    return c


def obter(sessao: Session, cliente_id: str) -> ClienteDB:
    c = sessao.get(ClienteDB, cliente_id)
    if c is None:
        raise ErroApi(401, "Cadastro não encontrado")
    return c


def _limpar_consentimento(c: ClienteDB) -> None:
    c.consentimento_id = None
    c.escopos = None
    c.score = None
    c.analise = None
    c.calculado_em = None


def atualizar(sessao: Session, operadora: Operadora, c: ClienteDB, dados: AtualizarDados) -> ClienteDB:
    mudancas = dados.model_dump(exclude_none=True)
    if mudancas.get("telefone", c.telefone) != c.telefone and c.consentimento_id:
        # O consentimento vale para a linha antiga: revoga e apaga a análise.
        operadora.revogar(c.consentimento_id)
        _limpar_consentimento(c)
    for campo, valor in mudancas.items():
        setattr(c, campo, valor)
    try:
        sessao.commit()
    except IntegrityError as exc:
        sessao.rollback()
        raise ErroApi(409, "Já existe um cadastro com este telefone") from exc
    return c


def consentir(sessao: Session, operadora: Operadora, c: ClienteDB, pedido: PedidoConsentimento) -> dict:
    if c.consentimento_id:
        raise ErroApi(409, "Você já tem um consentimento ativo: revogue-o antes de criar outro")
    consentimento = operadora.criar_consentimento(
        {
            "telefone": c.telefone,
            "cpf": c.cpf,
            "escopos": [e.value for e in pedido.escopos],
            "finalidade": FINALIDADE_CONSENTIMENTO,
            "solicitante": SOLICITANTE,
            "validade_dias": pedido.validade_dias,
        }
    )
    c.consentimento_id = consentimento["id"]
    c.escopos = [e.value for e in pedido.escopos]
    sessao.commit()
    return consentimento


def calcular(sessao: Session, operadora: Operadora, c: ClienteDB, pedido: PedidoScore) -> ClienteDB:
    if not c.consentimento_id:
        raise ErroApi(409, "Autorize o uso dos seus dados antes de calcular o score")
    dados = operadora.dados(c.telefone, c.consentimento_id)
    resultado = analisar_com_tratamento(dados, pedido.valor_solicitado)
    c.valor_solicitado = pedido.valor_solicitado
    c.finalidade = pedido.finalidade
    c.score = resultado.score
    c.analise = resultado.model_dump(mode="json")
    c.calculado_em = agora()
    sessao.commit()
    return c


def meu_score(c: ClienteDB) -> MeuScore:
    if not c.analise:
        raise ErroApi(404, "Você ainda não calculou o seu score")
    return MeuScore(
        valor_solicitado=c.valor_solicitado,
        finalidade=c.finalidade,
        calculado_em=c.calculado_em,
        escopos=c.escopos or [],
        analise=ResultadoAnalise.model_validate(c.analise),
    )


def revogar(sessao: Session, operadora: Operadora, c: ClienteDB) -> ClienteDB:
    """Revoga na operadora e apaga o score guardado. O cadastro continua."""
    if c.consentimento_id:
        operadora.revogar(c.consentimento_id)
        _limpar_consentimento(c)
        sessao.commit()
    return c
