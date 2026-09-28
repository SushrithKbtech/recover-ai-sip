"""Persistence layer sitting between the API and the LangGraph state.

The graph itself stays storage-agnostic: it receives a plain state dict and
returns one. Everything here is about turning that dict into rows and back.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ChatSession, Computation, Message


def _blank_state() -> dict:
    return {
        "messages": [],
        "scenario": None,
        "params": None,
        "missing_fields": [],
        "calculator_result": None,
        "calculator_error": None,
        "final_explanation": None,
        "assumptions": [],
        "awaiting_clarification": False,
        "clarifying_question": None,
    }


def load_state(db: Session, session_id: str) -> dict:
    """Rebuild graph state for a session.

    Only the durable fields are restored. Per-turn outputs (the calculator
    result, explanation, and clarifying question) start empty every turn so a
    stale answer from a previous turn can never be served as a fresh one.
    """
    row = db.get(ChatSession, session_id)
    if row is None:
        return _blank_state()

    messages = db.scalars(
        select(Message).where(Message.session_id == session_id).order_by(Message.id)
    ).all()

    state = _blank_state()
    state["messages"] = [{"role": m.role, "content": m.content} for m in messages]
    state["scenario"] = row.scenario
    state["params"] = row.params
    state["missing_fields"] = row.missing_fields or []
    state["awaiting_clarification"] = row.awaiting_clarification
    return state


def persist_turn(
    db: Session,
    session_id: str,
    state: dict,
    user_message: str,
    assistant_message: str,
) -> None:
    """Write one completed turn: session state, both transcript rows, and the
    calculation if this turn produced one. Called inside a single transaction."""
    row = db.get(ChatSession, session_id)
    if row is None:
        row = ChatSession(id=session_id)
        db.add(row)
        # Flush so the parent row exists before the FK rows below are inserted.
        db.flush()

    row.scenario = state.get("scenario")
    row.params = state.get("params")
    row.missing_fields = state.get("missing_fields") or []
    row.awaiting_clarification = bool(state.get("awaiting_clarification"))

    db.add_all(
        [
            Message(session_id=session_id, role="user", content=user_message),
            Message(session_id=session_id, role="assistant", content=assistant_message),
        ]
    )

    if state.get("calculator_result") and state.get("final_explanation"):
        db.add(
            Computation(
                session_id=session_id,
                scenario=state["scenario"],
                params=state.get("params") or {},
                result=state["calculator_result"],
            )
        )


def get_session(db: Session, session_id: str) -> ChatSession | None:
    return db.get(ChatSession, session_id)


def get_messages(db: Session, session_id: str) -> list[Message]:
    return list(
        db.scalars(
            select(Message).where(Message.session_id == session_id).order_by(Message.id)
        )
    )


def get_computations(db: Session, session_id: str) -> list[Computation]:
    return list(
        db.scalars(
            select(Computation)
            .where(Computation.session_id == session_id)
            .order_by(Computation.id)
        )
    )


def scenario_stats(db: Session) -> dict:
    """Aggregate of which scenarios actually get used, straight from SQL."""
    rows = db.execute(
        select(
            Computation.scenario,
            func.count(Computation.id),
            func.max(Computation.created_at),
        )
        .group_by(Computation.scenario)
        .order_by(func.count(Computation.id).desc())
    ).all()

    return {
        "total_sessions": db.scalar(select(func.count(ChatSession.id))) or 0,
        "total_computations": db.scalar(select(func.count(Computation.id))) or 0,
        "by_scenario": [
            {"scenario": scenario, "runs": runs, "last_run_at": last_run_at}
            for scenario, runs, last_run_at in rows
        ],
    }
