"""Persistência das solicitações e da trilha de auditoria (PostgreSQL via docker compose)."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

URL_PADRAO = "postgresql+psycopg://scorelyne:scorelyne@localhost:5432/scorelyne"


def agora() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class SolicitacaoDB(Base):
    __tablename__ = "solicitacoes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora, onupdate=agora)

    # Declarado pelo cliente no pedido
    nome: Mapped[str] = mapped_column(String(120))
    telefone: Mapped[str] = mapped_column(String(11), index=True)
    ocupacao: Mapped[str | None] = mapped_column(String(120))
    cidade: Mapped[str | None] = mapped_column(String(80))
    uf: Mapped[str | None] = mapped_column(String(2))
    valor_solicitado: Mapped[float] = mapped_column(Float)
    finalidade: Mapped[str] = mapped_column(String(200))

    # Consentimento e análise do agente
    consentimento_id: Mapped[str] = mapped_column(String(36))
    escopos: Mapped[list[str]] = mapped_column(JSON)
    plano: Mapped[str | None] = mapped_column(String(20))
    score: Mapped[int | None] = mapped_column(Integer)
    decisao_agente: Mapped[str] = mapped_column(String(20))
    analise: Mapped[dict | None] = mapped_column(JSON)  # ResultadoAnalise completo; apagado na revogação

    # Revisão humana
    decisao_final: Mapped[str | None] = mapped_column(String(20))
    justificativa: Mapped[str | None] = mapped_column(Text)
    analista: Mapped[str | None] = mapped_column(String(120))
    decidido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    eventos: Mapped[list[EventoDB]] = relationship(
        back_populates="solicitacao", order_by="EventoDB.id", cascade="all, delete-orphan"
    )


class EventoDB(Base):
    """Trilha de auditoria: só cresce, nunca é editada."""

    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitacao_id: Mapped[str] = mapped_column(ForeignKey("solicitacoes.id"), index=True)
    em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    ator: Mapped[str] = mapped_column(String(20))  # cliente | agente | analista | sistema
    tipo: Mapped[str] = mapped_column(String(40))
    titulo: Mapped[str] = mapped_column(String(200))
    detalhe: Mapped[str | None] = mapped_column(Text)

    solicitacao: Mapped[SolicitacaoDB] = relationship(back_populates="eventos")


def criar_sessoes(url: str | None = None) -> sessionmaker:
    url = url or os.getenv("BANCO_DB_URL", URL_PADRAO)
    if url.startswith("sqlite"):
        # Usado nos testes: banco em memória compartilhado entre threads.
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
