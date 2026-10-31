"""Regras do lado do consumidor: conta, consentimento, score, pedidos e controle dos próprios dados."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scorelyne.comum.analise import analisar_com_tratamento
from scorelyne.comum.auth import hash_senha, senha_confere
from scorelyne.comum.contratos import SituacaoSolicitacao, TrocaDeSenha
from scorelyne.comum.erros import ErroApi
from scorelyne.comum.operadora import Operadora
from scorelyne.score.analise import ResultadoAnalise

from .credor import Credor
from .db import ClienteDB, PedidoDB, agora
from .esquemas import (
    AtualizarDados,
    Cadastro,
    Cliente,
    ConsentimentoDetalhe,
    Login,
    MeuScore,
    PedidoConsentimento,
    PedidoEnviado,
    PedidoScore,
)

SOLICITANTE = "ScoreLyne"
FINALIDADE_CONSENTIMENTO = "autoconsulta_de_score"
CREDOR_NOME = "Banco Parceiro S.A."
FINALIDADE_CREDOR = "analise_de_credito"


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
        enviado_ao_credor=c.solicitacao_id is not None,
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


def atualizar(
    sessao: Session, operadora: Operadora, credor: Credor, c: ClienteDB, dados: AtualizarDados
) -> ClienteDB:
    mudancas = dados.model_dump(exclude_none=True)
    if mudancas.get("telefone", c.telefone) != c.telefone:
        # Os consentimentos valem para a linha antiga: revoga tudo e apaga as análises.
        _retirar_do_credor(sessao, credor, c, "dados_alterados")
        if c.consentimento_id:
            operadora.revogar_se_existir(c.consentimento_id)
        _limpar_consentimento(c)
    for campo, valor in mudancas.items():
        setattr(c, campo, valor)
    try:
        sessao.commit()
    except IntegrityError as exc:
        sessao.rollback()
        raise ErroApi(409, "Já existe um cadastro com este telefone") from exc
    return c


def trocar_senha(sessao: Session, c: ClienteDB, dados: TrocaDeSenha) -> None:
    if not senha_confere(dados.senha_atual, c.senha_hash):
        raise ErroApi(403, "A senha atual está incorreta")
    if dados.nova_senha == dados.senha_atual:
        raise ErroApi(422, "A nova senha precisa ser diferente da atual")
    c.senha_hash = hash_senha(dados.nova_senha)
    sessao.commit()


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


def _consentimento_perdido(sessao: Session, credor: Credor, c: ClienteDB) -> None:
    """A operadora não conhece mais um consentimento guardado aqui (ela guarda em memória e reiniciou).

    O acesso aos dados já não existe, então o estado local é encerrado: o pedido no credor é retirado,
    se ele estiver no ar, e a autorização e o score guardados saem. A pessoa autoriza de novo quando quiser.
    """
    try:
        _retirar_do_credor(sessao, credor, c, "consentimento_perdido")
    except ErroApi:
        pass  # credor fora do ar: o pedido segue marcado e pode ser retirado depois
    _limpar_consentimento(c)
    sessao.commit()


def consentimentos(
    sessao: Session, operadora: Operadora, credor: Credor, c: ClienteDB
) -> list[ConsentimentoDetalhe]:
    """Os consentimentos ativos da pessoa, com cada acesso que a operadora registrou aos dados dela."""
    saida = []
    for consentimento_id, destinatario in (
        (c.consentimento_id, SOLICITANTE),
        (c.consentimento_credor_id, CREDOR_NOME),
    ):
        if not consentimento_id:
            continue
        try:
            dados = operadora.consentimento(consentimento_id)
        except ErroApi as exc:
            if exc.status != 404:
                raise
            _consentimento_perdido(sessao, credor, c)
            return []
        saida.append(ConsentimentoDetalhe.model_validate({**dados, "destinatario": destinatario}))
    return saida


def calcular(sessao: Session, operadora: Operadora, c: ClienteDB, pedido: PedidoScore) -> ClienteDB:
    if not c.consentimento_id:
        raise ErroApi(409, "Autorize o uso dos seus dados antes de calcular o score")
    try:
        dados = operadora.dados(c.telefone, c.consentimento_id)
    except ErroApi as exc:
        if exc.status == 403:
            # Expirou, foi revogado ou a operadora o perdeu: o consentimento guardado aqui não serve mais.
            _limpar_consentimento(c)
            sessao.commit()
            raise ErroApi(
                409,
                "O seu consentimento não vale mais (expirou ou foi encerrado). Autorize de novo para calcular.",
            ) from exc
        raise
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


def _encerrar_pedido(sessao: Session, c: ClienteDB, motivo: str) -> None:
    if not c.solicitacao_id:
        return
    pedido = sessao.scalar(select(PedidoDB).where(PedidoDB.solicitacao_id == c.solicitacao_id))
    if pedido and pedido.encerrado_em is None:
        pedido.encerrado_em = agora()
        pedido.encerramento = motivo


def _retirar_do_credor(sessao: Session, credor: Credor, c: ClienteDB, motivo: str) -> None:
    """O credor revoga o consentimento dele na operadora e apaga a análise. Falhou? Nada muda aqui."""
    if c.solicitacao_id:
        credor.revogar(c.solicitacao_id)
        _encerrar_pedido(sessao, c, motivo)
        c.solicitacao_id = None
        c.consentimento_credor_id = None


def revogar(sessao: Session, operadora: Operadora, credor: Credor, c: ClienteDB) -> ClienteDB:
    """Revoga tudo: o envio ao credor, o consentimento na operadora e o score guardado."""
    _retirar_do_credor(sessao, credor, c, "consentimento_revogado")
    if c.consentimento_id:
        operadora.revogar_se_existir(c.consentimento_id)
        _limpar_consentimento(c)
    sessao.commit()
    return c


def enviar_ao_credor(sessao: Session, operadora: Operadora, credor: Credor, c: ClienteDB) -> ClienteDB:
    """Pede crédito ao credor. A pessoa dá ao credor um consentimento só dele, com os mesmos escopos."""
    if not c.analise:
        raise ErroApi(409, "Calcule o seu score antes de enviar o pedido ao credor")
    if c.solicitacao_id:
        raise ErroApi(409, "Seu pedido já foi enviado: retire-o antes de enviar de novo")

    consentimento = operadora.criar_consentimento(
        {
            "telefone": c.telefone,
            "cpf": c.cpf,
            "escopos": c.escopos,
            "finalidade": FINALIDADE_CREDOR,
            "solicitante": CREDOR_NOME,
        }
    )
    try:
        solicitacao = credor.criar(
            {
                "nome": c.nome,
                "telefone": c.telefone,
                "consentimento_id": consentimento["id"],
                "valor_solicitado": c.valor_solicitado,
                "finalidade": c.finalidade,
                "ocupacao": c.ocupacao,
                "cidade": c.cidade,
                "uf": c.uf,
            }
        )
    except ErroApi:
        operadora.revogar_se_existir(consentimento["id"])  # não deixa consentimento solto se o envio falhou
        raise
    c.solicitacao_id = solicitacao["id"]
    c.consentimento_credor_id = consentimento["id"]
    sessao.add(
        PedidoDB(
            id=str(uuid.uuid4()),
            cliente_id=c.id,
            solicitacao_id=solicitacao["id"],
            valor_solicitado=c.valor_solicitado,
            finalidade=c.finalidade,
        )
    )
    sessao.commit()
    return c


def retirar_do_credor(sessao: Session, credor: Credor, c: ClienteDB) -> ClienteDB:
    """Desfaz só o envio ao credor. O consentimento e o score do próprio consumidor continuam."""
    if not c.solicitacao_id:
        raise ErroApi(409, "Você não tem nenhum pedido enviado")
    _retirar_do_credor(sessao, credor, c, "retirado_pelo_cliente")
    sessao.commit()
    return c


def minha_solicitacao(credor: Credor, c: ClienteDB) -> dict:
    if not c.solicitacao_id:
        raise ErroApi(404, "Você ainda não enviou nenhum pedido ao credor")
    return credor.situacao(c.solicitacao_id)


def pedidos(sessao: Session, credor: Credor, c: ClienteDB) -> list[PedidoEnviado]:
    """Histórico dos pedidos ao credor. Só o que ainda está aberto consulta a situação atual."""
    linhas = sessao.scalars(
        select(PedidoDB).where(PedidoDB.cliente_id == c.id).order_by(PedidoDB.enviado_em.desc())
    ).all()
    saida = []
    for p in linhas:
        situacao = None
        if p.encerrado_em is None:
            try:
                situacao = SituacaoSolicitacao.model_validate(credor.situacao(p.solicitacao_id))
            except ErroApi:
                situacao = None  # credor fora do ar: o histórico continua aparecendo
        saida.append(
            PedidoEnviado(
                id=p.id,
                valor_solicitado=p.valor_solicitado,
                finalidade=p.finalidade,
                enviado_em=p.enviado_em,
                encerrado_em=p.encerrado_em,
                encerramento=p.encerramento,
                situacao=situacao,
            )
        )
    return saida


def excluir_conta(sessao: Session, operadora: Operadora, credor: Credor, c: ClienteDB, senha: str) -> None:
    """Direito de exclusão (LGPD): revoga tudo e apaga o cadastro, o score e o histórico de pedidos.

    Se o credor estiver fora do ar, o consentimento dele é revogado direto na operadora, o que bloqueia
    qualquer leitura nova; a análise que o credor já guardava só some quando ele voltar e processar a
    revogação. Se a operadora também falhar, a exclusão é recusada, para nunca deixar acesso aberto.
    """
    if not senha_confere(senha, c.senha_hash):
        raise ErroApi(403, "A senha está incorreta")
    if c.solicitacao_id:
        try:
            credor.revogar(c.solicitacao_id)
        except ErroApi:
            if c.consentimento_credor_id:
                operadora.revogar_se_existir(c.consentimento_credor_id)
    if c.consentimento_id:
        operadora.revogar_se_existir(c.consentimento_id)
    sessao.execute(delete(PedidoDB).where(PedidoDB.cliente_id == c.id))
    sessao.delete(c)
    sessao.commit()
