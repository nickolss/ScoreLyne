"""Persistência do consumidor: cadastro e o último score calculado. Banco próprio, separado do credor."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

URL_PADRAO = "postgresql+psycopg://scorelyne:scorelyne@localhost:5432/scorelyne"


def agora() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ClienteDB(Base):
    __tablename__ = "clientes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    nome: Mapped[str] = mapped_column(String(120))
    cpf: Mapped[str] = mapped_column(String(11), unique=True)
    telefone: Mapped[str] = mapped_column(String(11), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    ocupacao: Mapped[str | None] = mapped_column(String(120))
    cidade: Mapped[str | None] = mapped_column(String(80))
    uf: Mapped[str | None] = mapped_column(String(2))

    # Consentimento dado à ScoreLyne para ler os dados da operadora
    consentimento_id: Mapped[str | None] = mapped_column(String(36))
    escopos: Mapped[list[str] | None] = mapped_column(JSON)

    # Solicitação enviada ao credor, com o consentimento específico dado a ele
    solicitacao_id: Mapped[str | None] = mapped_column(String(36))
    consentimento_credor_id: Mapped[str | None] = mapped_column(String(36))

    # Último score calculado; apagado quando o consentimento é revogado
    valor_solicitado: Mapped[float | None] = mapped_column(Float)
    finalidade: Mapped[str | None] = mapped_column(String(200))
    score: Mapped[int | None] = mapped_column(Integer)
    analise: Mapped[dict | None] = mapped_column(JSON)
    calculado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PedidoDB(Base):
    """Cada pedido enviado ao credor. Fica mesmo depois de retirado, para a pessoa ver o histórico."""

    __tablename__ = "pedidos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(36), index=True)
    solicitacao_id: Mapped[str] = mapped_column(String(36), unique=True)
    valor_solicitado: Mapped[float] = mapped_column(Float)
    finalidade: Mapped[str] = mapped_column(String(200))
    enviado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    encerrado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # retirado_pelo_cliente | consentimento_revogado | dados_alterados
    encerramento: Mapped[str | None] = mapped_column(String(40))


def criar_sessoes(url: str | None = None) -> sessionmaker:
    url = url or os.getenv("CONSUMIDOR_DB_URL", URL_PADRAO)
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
