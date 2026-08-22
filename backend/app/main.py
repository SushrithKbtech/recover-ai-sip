from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.graph import get_graph
from app.schemas import ChatRequest, ChatResponse, ResultPayload

app = FastAPI(title="RecoverAI API")

_origins_env = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store: session_id -> partial graph state.
# No database required for this project's scope.
_sessions: dict[str, dict] = {}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    session = _sessions.get(req.session_id)
    if session is None:
        session = {
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

    session["messages"].append({"role": "user", "content": req.message})
    # Reset per-turn fields; conversation history (messages, and previously
    # extracted params/scenario) carries forward so intent_parser can merge
    # new info with what it already knows.
    session["clarifying_question"] = None
    session["calculator_error"] = None

    graph = get_graph()
    result_state = graph.invoke(session)
    _sessions[req.session_id] = result_state

    if result_state.get("clarifying_question"):
        question = result_state["clarifying_question"]
        result_state["messages"].append({"role": "assistant", "content": question})
        return ChatResponse(
            session_id=req.session_id,
            type="clarifying_question",
            message=question,
            result=None,
        )

    if result_state.get("final_explanation"):
        explanation = result_state["final_explanation"]
        lead_in = "Here's how those two scenarios compare:"
        result_state["messages"].append({"role": "assistant", "content": lead_in})
        return ChatResponse(
            session_id=req.session_id,
            type="result",
            message=lead_in,
            result=ResultPayload(
                scenario=result_state["scenario"],
                calculator_output=result_state["calculator_result"],
                explanation=explanation,
                assumptions=result_state.get("assumptions", []),
            ),
        )

    # Should not normally happen; fail safe rather than crash.
    return ChatResponse(
        session_id=req.session_id,
        type="error",
        message="Something went wrong processing that request. Please try rephrasing.",
        result=None,
    )
