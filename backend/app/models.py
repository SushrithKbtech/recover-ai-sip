"""ORM models for conversation state, transcripts, and calculation history."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ChatSession(Base):
    """One conversation. Holds the durable slice of the LangGraph state, so a
    session survives a backend restart and can be resumed on any instance."""

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario: Mapped[str | None] = mapped_column(String(64), index=True)
    params: Mapped[dict | None] = mapped_column(JSON)
    missing_fields: Mapped[list | None] = mapped_column(JSON)
    awaiting_clarification: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), index=True
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    computations: Mapped[list["Computation"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    """A single turn of the transcript, replayed into the graph on each request."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="messages")

    # Every turn re-reads the whole transcript for one session in insertion
    # order, so this composite covers the hot path as a single range scan.
    __table_args__ = (Index("ix_messages_session_id_id", "session_id", "id"),)


class Computation(Base):
    """A completed calculator run, kept for history and scenario analytics."""

    __tablename__ = "computations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    scenario: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[ChatSession] = relationship(back_populates="computations")

    __table_args__ = (
        Index("ix_computations_session_id_id", "session_id", "id"),
        Index("ix_computations_scenario_created_at", "scenario", "created_at"),
    )
