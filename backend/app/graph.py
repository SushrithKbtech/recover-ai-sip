"""
LangGraph agent flow for RecoverAI.

    START -> intent_parser -> [clarify | calculator_dispatch]
    clarify -> END (waits for the next user turn, then re-enters intent_parser)
    calculator_dispatch -> [explainer | clarify]
    explainer -> END

Only `intent_parser` and `explainer` call the LLM. `calculator_dispatch` is
pure deterministic Python (see app/calculators.py) and must never call an
LLM or make arithmetic decisions itself.
"""
from __future__ import annotations

import json
import os
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, START, END
from openai import OpenAI

from app.calculators import (
    CalculatorValidationError,
    calculate_emi_comparison,
    calculate_opportunity_cost,
    calculate_sip_pause_vs_loan_payoff,
)
from app.schemas import ExtractedParams

REQUIRED_FIELDS = {
    "sip_pause_vs_loan_payoff": [
        "monthly_sip_amount",
        "expected_annual_return_pct",
        "loan_outstanding_amount",
        "loan_interest_rate_pct",
        "loan_remaining_tenure_months",
        "pause_duration_months",
    ],
    "emi_comparison": ["offers"],
    "opportunity_cost": [
        "lump_sum_amount",
        "loan_interest_rate_pct",
        "investment_expected_return_pct",
        "time_horizon_months",
    ],
}

SCENARIO_DESCRIPTIONS = """\
1. sip_pause_vs_loan_payoff — pausing/redirecting a SIP to pay off a loan faster
   vs continuing the SIP as-is.
2. emi_comparison — comparing two or more loan offers (principal, rate, tenure)
   to see which has the lower EMI / total interest.
3. opportunity_cost — investing a lump sum vs using it to prepay a loan.
4. out_of_scope — anything that isn't one of the above (e.g. general advice,
   tax questions, unrelated topics). Use this rather than guessing.
"""


def _get_client() -> OpenAI:
    base_url = os.environ.get("OPENAI_BASE_URL")
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=base_url) if base_url else OpenAI(
        api_key=os.environ["OPENAI_API_KEY"]
    )


def _model_name() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


class RecoverAIState(TypedDict):
    messages: list
    scenario: Optional[str]
    params: Optional[dict]
    missing_fields: list[str]
    calculator_result: Optional[dict]
    calculator_error: Optional[str]
    final_explanation: Optional[str]
    assumptions: list[str]
    awaiting_clarification: bool
    clarifying_question: Optional[str]


# ---------------------------------------------------------------------------
# Node: intent_parser (LLM, structured output)
# ---------------------------------------------------------------------------

INTENT_PARSER_SYSTEM_PROMPT = f"""You are the intent-parsing module of RecoverAI, a personal-finance \
"what if" simulator. You do NOT do any arithmetic yourself. Your only job is to:

1. Decide which calculator scenario the user's message maps to:
{SCENARIO_DESCRIPTIONS}
2. Extract every numeric parameter that scenario needs from the conversation
   so far (including any prior clarifying answers).
3. If required parameters are still missing or ambiguous, set
   clarification_needed=true and list exactly which fields are missing in
   missing_fields (use the field names as given in the schema).
4. If scenario is out_of_scope, set clarification_needed=false and leave
   other fields empty.

Never invent numbers the user didn't provide. Respond only with the
structured JSON matching the given schema."""


def intent_parser_node(state: RecoverAIState) -> RecoverAIState:
    client = _get_client()
    conversation = "\n".join(
        f"{m['role']}: {m['content']}" for m in state["messages"]
    )
    try:
        completion = client.beta.chat.completions.parse(
            model=_model_name(),
            messages=[
                {"role": "system", "content": INTENT_PARSER_SYSTEM_PROMPT},
                {"role": "user", "content": conversation},
            ],
            response_format=ExtractedParams,
        )
        extracted = completion.choices[0].message.parsed
    except Exception:
        # Malformed / unparseable structured output -> route to clarify,
        # never crash the graph.
        state["scenario"] = None
        state["missing_fields"] = []
        state["awaiting_clarification"] = True
        state["clarifying_question"] = (
            "Sorry, I couldn't quite parse that. Could you rephrase your "
            "question with the specific numbers involved (amounts, rates, "
            "and time periods)?"
        )
        return state

    params = extracted.model_dump(exclude={"scenario", "missing_fields", "clarification_needed"})
    params = {k: v for k, v in params.items() if v is not None}

    state["scenario"] = extracted.scenario
    state["params"] = params
    state["missing_fields"] = extracted.missing_fields

    if extracted.scenario == "out_of_scope":
        state["awaiting_clarification"] = False
        state["calculator_error"] = "out_of_scope"
        return state

    # Cross-check against our own required-fields list in case the LLM
    # missed something.
    required = REQUIRED_FIELDS.get(extracted.scenario, [])
    truly_missing = [f for f in required if f not in params or params[f] in (None, [])]
    if truly_missing or extracted.clarification_needed:
        state["missing_fields"] = list(dict.fromkeys(state["missing_fields"] + truly_missing))
        state["awaiting_clarification"] = True
    else:
        state["awaiting_clarification"] = False

    return state


def route_after_intent_parser(state: RecoverAIState) -> str:
    if state.get("calculator_error") == "out_of_scope":
        return "out_of_scope"
    if state.get("awaiting_clarification"):
        return "clarify"
    return "calculator_dispatch"


# ---------------------------------------------------------------------------
# Node: clarify (LLM, generates a natural-language question)
# ---------------------------------------------------------------------------

def clarify_node(state: RecoverAIState) -> RecoverAIState:
    if state.get("clarifying_question"):
        # already set (e.g. by malformed-output fallback)
        return state

    missing = state.get("missing_fields", [])
    calc_error = state.get("calculator_error")

    if calc_error and calc_error != "out_of_scope":
        question = (
            f"That input isn't valid: {calc_error}. Could you provide a "
            "corrected value?"
        )
        state["clarifying_question"] = question
        return state

    client = _get_client()
    prompt = (
        "The user is asking about a financial 'what if' scenario. We still "
        f"need these fields to run the calculation: {', '.join(missing)}. "
        "Write ONE short, friendly clarifying question asking specifically "
        "for this missing information. Do not ask for anything already "
        "provided."
    )
    try:
        completion = client.chat.completions.create(
            model=_model_name(),
            messages=[{"role": "user", "content": prompt}],
        )
        question = completion.choices[0].message.content.strip()
    except Exception:
        question = f"Could you share the following details: {', '.join(missing)}?"

    state["clarifying_question"] = question
    return state


# ---------------------------------------------------------------------------
# Node: calculator_dispatch (pure Python, NO LLM CALL)
# ---------------------------------------------------------------------------

def calculator_dispatch_node(state: RecoverAIState) -> RecoverAIState:
    scenario = state["scenario"]
    params = state.get("params") or {}
    state["calculator_error"] = None

    try:
        if scenario == "sip_pause_vs_loan_payoff":
            result = calculate_sip_pause_vs_loan_payoff(
                monthly_sip_amount=params["monthly_sip_amount"],
                expected_annual_return_pct=params["expected_annual_return_pct"],
                loan_outstanding_amount=params["loan_outstanding_amount"],
                loan_interest_rate_pct=params["loan_interest_rate_pct"],
                loan_remaining_tenure_months=int(params["loan_remaining_tenure_months"]),
                pause_duration_months=int(params["pause_duration_months"]),
            )
        elif scenario == "emi_comparison":
            offers = [o if isinstance(o, dict) else o.__dict__ for o in params["offers"]]
            result = calculate_emi_comparison(offers)
        elif scenario == "opportunity_cost":
            result = calculate_opportunity_cost(
                lump_sum_amount=params["lump_sum_amount"],
                loan_interest_rate_pct=params["loan_interest_rate_pct"],
                investment_expected_return_pct=params["investment_expected_return_pct"],
                time_horizon_months=int(params["time_horizon_months"]),
            )
        else:
            raise CalculatorValidationError(f"Unknown scenario: {scenario}")
    except CalculatorValidationError as e:
        state["calculator_error"] = str(e)
        state["calculator_result"] = None
        return state
    except (KeyError, TypeError) as e:
        state["calculator_error"] = f"Missing or invalid input: {e}"
        state["calculator_result"] = None
        return state

    state["calculator_result"] = result
    return state


def route_after_calculator(state: RecoverAIState) -> str:
    if state.get("calculator_error"):
        return "clarify"
    return "explainer"


# ---------------------------------------------------------------------------
# Node: explainer (LLM, grounded strictly in calculator_result)
# ---------------------------------------------------------------------------

EXPLAINER_SYSTEM_PROMPT = """You are the explanation module of RecoverAI. You are given the raw \
output of a deterministic financial calculator as JSON. Write a plain-language \
comparison of the scenarios.

CRITICAL CONSTRAINT: every number you mention MUST come directly from the \
provided JSON. Do not compute, estimate, or invent any new figures. If you \
need to describe a difference, use the values already present in the JSON \
(e.g. a "comparison" object) rather than calculating it yourself.

Respond with a JSON object with exactly these keys:
- "summary": one paragraph plain-language summary
- "key_differences": a list of short bullet strings
- "assumptions": a list of strings, one per simplification made (e.g. fixed \
interest rate, no tax implications, no prepayment penalties considered). \
Always include at least 2-3 generic assumptions plus any scenario-specific \
ones. If the scenario involves investment returns, explicitly state that \
investment returns are projected and not guaranteed, while loan interest \
savings are guaranteed."""


def explainer_node(state: RecoverAIState) -> RecoverAIState:
    client = _get_client()
    payload = {
        "scenario": state["scenario"],
        "calculator_output": state["calculator_result"],
    }
    try:
        completion = client.chat.completions.create(
            model=_model_name(),
            messages=[
                {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload)},
            ],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(completion.choices[0].message.content)
        summary = parsed.get("summary", "")
        bullets = parsed.get("key_differences", [])
        assumptions = parsed.get("assumptions", [])
        explanation_text = summary
        if bullets:
            explanation_text += "\n\n" + "\n".join(f"- {b}" for b in bullets)
    except Exception:
        explanation_text = (
            "Here's how the two scenarios compare based on the numbers "
            "calculated above."
        )
        assumptions = [
            "Assumes a fixed interest rate for the full tenure.",
            "Does not account for taxes, fees, or prepayment penalties.",
        ]

    if not assumptions:
        assumptions = [
            "Assumes a fixed interest rate for the full tenure.",
            "Does not account for taxes, fees, or prepayment penalties.",
        ]

    state["final_explanation"] = explanation_text
    state["assumptions"] = assumptions
    return state


# ---------------------------------------------------------------------------
# Out-of-scope terminal node
# ---------------------------------------------------------------------------

def out_of_scope_node(state: RecoverAIState) -> RecoverAIState:
    state["final_explanation"] = None
    state["clarifying_question"] = (
        "RecoverAI only handles three scenarios: pausing a SIP to pay off a "
        "loan faster, comparing loan/EMI offers, and weighing investing a "
        "lump sum vs prepaying a loan. Could you rephrase your question to "
        "fit one of those, or ask something else within that scope?"
    )
    return state


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(RecoverAIState)

    graph.add_node("intent_parser", intent_parser_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("calculator_dispatch", calculator_dispatch_node)
    graph.add_node("explainer", explainer_node)
    graph.add_node("out_of_scope", out_of_scope_node)

    graph.add_edge(START, "intent_parser")
    graph.add_conditional_edges(
        "intent_parser",
        route_after_intent_parser,
        {
            "clarify": "clarify",
            "calculator_dispatch": "calculator_dispatch",
            "out_of_scope": "out_of_scope",
        },
    )
    graph.add_conditional_edges(
        "calculator_dispatch",
        route_after_calculator,
        {"clarify": "clarify", "explainer": "explainer"},
    )
    graph.add_edge("clarify", END)
    graph.add_edge("explainer", END)
    graph.add_edge("out_of_scope", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
