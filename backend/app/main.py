from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import repository
from app.db import SessionLocal, engine, init_db
from app.graph import get_graph
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ResultPayload,
    SessionHistoryResponse,
    StatsResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="RecoverAI API", lifespan=lifespan)

_origins_env = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    with SessionLocal.begin() as db:
        state = repository.load_state(db, req.session_id)

    state["messages"].append({"role": "user", "content": req.message})

    # Run the graph outside any transaction: these are multi-second LLM calls
    # and holding a pooled connection across them would starve the pool.
    result_state = get_graph().invoke(state)

    if result_state.get("clarifying_question"):
        reply = result_state["clarifying_question"]
        response = ChatResponse(
            session_id=req.session_id,
            type="clarifying_question",
            message=reply,
            result=None,
        )
    elif result_state.get("final_explanation"):
        reply = "Here's how those two scenarios compare:"
        response = ChatResponse(
            session_id=req.session_id,
            type="result",
            message=reply,
            result=ResultPayload(
                scenario=result_state["scenario"],
                calculator_output=result_state["calculator_result"],
                explanation=result_state["final_explanation"],
                assumptions=result_state.get("assumptions", []),
            ),
        )
    else:
        reply = "Something went wrong processing that request. Please try rephrasing."
        response = ChatResponse(
            session_id=req.session_id,
            type="error",
            message=reply,
            result=None,
        )

    with SessionLocal.begin() as db:
        repository.persist_turn(db, req.session_id, result_state, req.message, reply)

    return response


@app.get("/api/sessions/{session_id}/history", response_model=SessionHistoryResponse)
def session_history(session_id: str):
    with SessionLocal.begin() as db:
        session = repository.get_session(db, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")

        return SessionHistoryResponse(
            session_id=session.id,
            scenario=session.scenario,
            awaiting_clarification=session.awaiting_clarification,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=repository.get_messages(db, session_id),
            computations=repository.get_computations(db, session_id),
        )


@app.get("/api/stats", response_model=StatsResponse)
def stats():
    with SessionLocal.begin() as db:
        return repository.scenario_stats(db)
