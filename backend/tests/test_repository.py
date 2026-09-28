"""Integration tests for the MySQL persistence layer.

These hit a real MySQL (the point is to catch schema, FK, and JSON-column
problems that an in-memory fake would hide), so they skip when DATABASE_URL
isn't reachable. Start one with `docker compose up -d mysql` from the repo root.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app import repository
from app.db import SessionLocal, engine, init_db
from app.models import ChatSession


def _db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="MySQL not reachable at DATABASE_URL",
)


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture
def session_id():
    sid = f"test-{uuid.uuid4()}"
    yield sid
    with SessionLocal.begin() as db:
        row = db.get(ChatSession, sid)
        if row is not None:
            db.delete(row)


def test_unknown_session_starts_blank(session_id):
    with SessionLocal.begin() as db:
        state = repository.load_state(db, session_id)

    assert state["messages"] == []
    assert state["scenario"] is None
    assert state["awaiting_clarification"] is False


def test_turn_round_trips_through_mysql(session_id):
    state = {
        "scenario": "emi_comparison",
        "params": {"offers": [{"principal": 500000}]},
        "missing_fields": ["tenure_months"],
        "awaiting_clarification": True,
    }

    with SessionLocal.begin() as db:
        repository.persist_turn(
            db, session_id, state, "compare two loans", "What tenure?"
        )

    with SessionLocal.begin() as db:
        loaded = repository.load_state(db, session_id)

    assert loaded["scenario"] == "emi_comparison"
    assert loaded["params"] == {"offers": [{"principal": 500000}]}
    assert loaded["missing_fields"] == ["tenure_months"]
    assert loaded["awaiting_clarification"] is True
    assert loaded["messages"] == [
        {"role": "user", "content": "compare two loans"},
        {"role": "assistant", "content": "What tenure?"},
    ]


def test_transcript_keeps_insertion_order_across_turns(session_id):
    with SessionLocal.begin() as db:
        repository.persist_turn(db, session_id, {}, "first", "reply one")
    with SessionLocal.begin() as db:
        repository.persist_turn(db, session_id, {}, "second", "reply two")

    with SessionLocal.begin() as db:
        loaded = repository.load_state(db, session_id)

    assert [m["content"] for m in loaded["messages"]] == [
        "first",
        "reply one",
        "second",
        "reply two",
    ]


def test_completed_calculation_is_recorded(session_id):
    state = {
        "scenario": "opportunity_cost",
        "params": {"lump_sum_amount": 200000},
        "calculator_result": {"comparison": {"projected_advantage_of_investing": 14664.22}},
        "final_explanation": "Investing looks better here.",
    }

    with SessionLocal.begin() as db:
        repository.persist_turn(db, session_id, state, "invest or prepay?", "Here you go")

    with SessionLocal.begin() as db:
        computations = repository.get_computations(db, session_id)

    assert len(computations) == 1
    assert computations[0].scenario == "opportunity_cost"
    assert computations[0].result["comparison"]["projected_advantage_of_investing"] == 14664.22


def test_clarifying_turn_records_no_calculation(session_id):
    state = {"scenario": "emi_comparison", "awaiting_clarification": True}

    with SessionLocal.begin() as db:
        repository.persist_turn(db, session_id, state, "compare loans", "What principal?")

    with SessionLocal.begin() as db:
        assert repository.get_computations(db, session_id) == []


def test_stale_result_is_not_replayed_on_next_turn(session_id):
    """A previous turn's answer must not survive into the next turn's state,
    or a clarifying question could be served alongside a stale result."""
    state = {
        "scenario": "opportunity_cost",
        "params": {"lump_sum_amount": 200000},
        "calculator_result": {"comparison": {}},
        "final_explanation": "Investing looks better here.",
    }

    with SessionLocal.begin() as db:
        repository.persist_turn(db, session_id, state, "invest or prepay?", "Here you go")

    with SessionLocal.begin() as db:
        loaded = repository.load_state(db, session_id)

    assert loaded["calculator_result"] is None
    assert loaded["final_explanation"] is None
    assert loaded["clarifying_question"] is None


def test_deleting_a_session_cascades_to_children(session_id):
    state = {
        "scenario": "opportunity_cost",
        "params": {"lump_sum_amount": 1},
        "calculator_result": {"x": 1},
        "final_explanation": "done",
    }
    with SessionLocal.begin() as db:
        repository.persist_turn(db, session_id, state, "hello", "hi")

    with SessionLocal.begin() as db:
        db.delete(db.get(ChatSession, session_id))

    with SessionLocal.begin() as db:
        assert repository.get_messages(db, session_id) == []
        assert repository.get_computations(db, session_id) == []
