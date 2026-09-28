"""Pydantic schemas for API I/O and structured LLM output."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Scenario = Literal[
    "sip_pause_vs_loan_payoff",
    "emi_comparison",
    "opportunity_cost",
    "out_of_scope",
]


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResultPayload(BaseModel):
    scenario: str
    calculator_output: dict
    explanation: str
    assumptions: list[str]


class ChatResponse(BaseModel):
    session_id: str
    type: Literal["clarifying_question", "result", "error"]
    message: str
    result: Optional[ResultPayload] = None


# --- Persisted history and analytics ---

class HistoryMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime


class HistoryComputation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario: str
    params: dict
    result: dict
    created_at: datetime


class SessionHistoryResponse(BaseModel):
    session_id: str
    scenario: Optional[str] = None
    awaiting_clarification: bool
    created_at: datetime
    updated_at: datetime
    messages: list[HistoryMessage]
    computations: list[HistoryComputation]


class ScenarioStat(BaseModel):
    scenario: str
    runs: int
    last_run_at: datetime


class StatsResponse(BaseModel):
    total_sessions: int
    total_computations: int
    by_scenario: list[ScenarioStat]


# --- Structured output schema the LLM must fill in for intent_parser ---

class LoanOffer(BaseModel):
    label: Optional[str] = None
    principal: Optional[float] = None
    annual_interest_rate_pct: Optional[float] = None
    tenure_months: Optional[int] = None


class ExtractedParams(BaseModel):
    """Structured extraction result. Every field is optional because the
    intent_parser may only have partial information after the first message;
    missing_fields is what drives the clarify branch."""

    scenario: Scenario = Field(description="Which of the 3 calculators applies, or out_of_scope")

    # sip_pause_vs_loan_payoff
    monthly_sip_amount: Optional[float] = None
    expected_annual_return_pct: Optional[float] = None
    loan_outstanding_amount: Optional[float] = None
    loan_interest_rate_pct: Optional[float] = None
    loan_remaining_tenure_months: Optional[int] = None
    pause_duration_months: Optional[int] = None

    # emi_comparison
    offers: Optional[list[LoanOffer]] = None

    # opportunity_cost
    lump_sum_amount: Optional[float] = None
    investment_expected_return_pct: Optional[float] = None
    time_horizon_months: Optional[int] = None

    missing_fields: list[str] = Field(default_factory=list)
    clarification_needed: bool = False
