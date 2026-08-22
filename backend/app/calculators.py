"""
Deterministic financial calculator functions.

HARD CONSTRAINT: this module must contain zero LLM/API calls. Every function
here is pure Python arithmetic and must be independently unit-testable
without any network access or mocking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class CalculatorValidationError(ValueError):
    """Raised when calculator inputs fail validation. Message is user-facing."""


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

def sip_future_value(monthly_amount: float, annual_return_pct: float, months: int) -> float:
    """Future value of a monthly SIP using the standard annuity-due formula.

    FV = P * [(1+r)^n - 1] / r * (1+r), r = monthly rate, n = months.
    Falls back to P * n when r == 0 (0% expected return).
    """
    if months <= 0:
        return 0.0
    r = annual_return_pct / 12 / 100
    if r == 0:
        return monthly_amount * months
    return monthly_amount * (((1 + r) ** months - 1) / r) * (1 + r)


def emi_amount(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """Standard EMI formula. Handles 0% interest as a straight-line special case."""
    if tenure_months <= 0:
        raise CalculatorValidationError("Loan tenure must be a positive number of months.")
    r = annual_rate_pct / 12 / 100
    if r == 0:
        return principal / tenure_months
    factor = (1 + r) ** tenure_months
    return principal * r * factor / (factor - 1)


@dataclass
class AmortizationResult:
    schedule: list[dict] = field(default_factory=list)
    months_taken: int = 0
    total_interest_paid: float = 0.0
    total_paid: float = 0.0
    payoff_before_term: bool = False


def build_amortization_schedule(
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
    emi: Optional[float] = None,
    extra_payments: Optional[dict[int, float]] = None,
) -> AmortizationResult:
    """Builds a month-by-month amortization schedule.

    `extra_payments` maps month index (1-based) -> extra principal payment
    applied that month, e.g. lump sums redirected from a paused SIP.
    """
    if principal <= 0:
        raise CalculatorValidationError("Loan outstanding amount must be positive.")
    if annual_rate_pct < 0:
        raise CalculatorValidationError("Interest rate cannot be negative.")
    if tenure_months <= 0:
        raise CalculatorValidationError("Loan tenure must be a positive number of months.")

    extra_payments = extra_payments or {}
    r = annual_rate_pct / 12 / 100
    monthly_emi = emi if emi is not None else emi_amount(principal, annual_rate_pct, tenure_months)

    balance = principal
    schedule: list[dict] = []
    total_interest = 0.0
    total_paid = 0.0
    month = 0

    # Safety cap: never iterate more than 2x the original tenure (or 1200
    # months) to avoid pathological infinite loops on bad input.
    max_months = max(tenure_months * 2, 60)

    while balance > 0.01 and month < max_months:
        month += 1
        interest_component = balance * r
        principal_component = min(monthly_emi - interest_component, balance)
        if principal_component < 0:
            # EMI doesn't even cover interest -- loan never amortizes.
            raise CalculatorValidationError(
                "This EMI does not cover the monthly interest; the loan would never be paid off."
            )
        extra = extra_payments.get(month, 0.0)
        extra = min(extra, balance - principal_component) if extra > 0 else 0.0
        balance -= (principal_component + extra)
        balance = max(balance, 0.0)

        paid_this_month = interest_component + principal_component + extra
        total_interest += interest_component
        total_paid += paid_this_month

        schedule.append({
            "month": month,
            "interest": round(interest_component, 2),
            "principal": round(principal_component, 2),
            "extra_payment": round(extra, 2),
            "balance": round(balance, 2),
        })

    return AmortizationResult(
        schedule=schedule,
        months_taken=month,
        total_interest_paid=round(total_interest, 2),
        total_paid=round(total_paid, 2),
        payoff_before_term=month < tenure_months,
    )


# ---------------------------------------------------------------------------
# 4a. SIP-Pause-vs-Loan-Payoff
# ---------------------------------------------------------------------------

def calculate_sip_pause_vs_loan_payoff(
    monthly_sip_amount: float,
    expected_annual_return_pct: float,
    loan_outstanding_amount: float,
    loan_interest_rate_pct: float,
    loan_remaining_tenure_months: int,
    pause_duration_months: int,
) -> dict:
    if monthly_sip_amount <= 0:
        raise CalculatorValidationError("Monthly SIP amount must be positive.")
    if expected_annual_return_pct < 0:
        raise CalculatorValidationError("Expected annual return cannot be negative.")
    if loan_interest_rate_pct < 0:
        raise CalculatorValidationError("Loan interest rate cannot be negative.")
    if pause_duration_months <= 0:
        raise CalculatorValidationError("Pause duration must be a positive number of months.")
    if pause_duration_months > loan_remaining_tenure_months:
        raise CalculatorValidationError(
            "Pause duration cannot exceed the loan's remaining tenure."
        )

    # --- Scenario A: continue SIP, minimum loan payment ---
    scenario_a_amort = build_amortization_schedule(
        loan_outstanding_amount, loan_interest_rate_pct, loan_remaining_tenure_months
    )
    scenario_a_corpus = sip_future_value(
        monthly_sip_amount, expected_annual_return_pct, loan_remaining_tenure_months
    )

    # --- Scenario B: pause SIP, redirect paused contributions as extra principal ---
    emi = emi_amount(loan_outstanding_amount, loan_interest_rate_pct, loan_remaining_tenure_months)
    extra_payments = {m: monthly_sip_amount for m in range(1, pause_duration_months + 1)}
    scenario_b_amort = build_amortization_schedule(
        loan_outstanding_amount,
        loan_interest_rate_pct,
        loan_remaining_tenure_months,
        emi=emi,
        extra_payments=extra_payments,
    )

    # SIP corpus in scenario B: no contributions during the pause, then
    # resumes for the remaining months, each contribution still growing to
    # the horizon end (loan_remaining_tenure_months).
    resumed_months = loan_remaining_tenure_months - pause_duration_months
    scenario_b_corpus = sip_future_value(
        monthly_sip_amount, expected_annual_return_pct, resumed_months
    )

    interest_saved = round(scenario_a_amort.total_interest_paid - scenario_b_amort.total_interest_paid, 2)
    months_reduced = scenario_a_amort.months_taken - scenario_b_amort.months_taken
    corpus_difference = round(scenario_b_corpus - scenario_a_corpus, 2)
    net_difference = round(interest_saved + corpus_difference, 2)

    return {
        "scenario_a": {
            "label": "Continue SIP",
            "loan_total_interest": scenario_a_amort.total_interest_paid,
            "loan_months_taken": scenario_a_amort.months_taken,
            "sip_final_corpus": round(scenario_a_corpus, 2),
            "loan_balance_over_time": [row["balance"] for row in scenario_a_amort.schedule],
        },
        "scenario_b": {
            "label": "Pause & Pay Off Loan",
            "loan_total_interest": scenario_b_amort.total_interest_paid,
            "loan_months_taken": scenario_b_amort.months_taken,
            "sip_final_corpus": round(scenario_b_corpus, 2),
            "loan_balance_over_time": [row["balance"] for row in scenario_b_amort.schedule],
        },
        "comparison": {
            "loan_interest_saved": interest_saved,
            "loan_tenure_reduced_months": months_reduced,
            "sip_corpus_difference": corpus_difference,
            "net_financial_difference": net_difference,
        },
    }


# ---------------------------------------------------------------------------
# 4b. EMI Comparison
# ---------------------------------------------------------------------------

def calculate_emi_comparison(offers: list[dict]) -> dict:
    if len(offers) < 2:
        raise CalculatorValidationError("Provide at least two loan offers to compare.")

    results = []
    for i, offer in enumerate(offers):
        principal = offer.get("principal")
        rate = offer.get("annual_interest_rate_pct")
        tenure = offer.get("tenure_months")
        label = offer.get("label", f"Offer {i + 1}")

        if principal is None or principal <= 0:
            raise CalculatorValidationError(f"{label}: principal must be positive.")
        if rate is None or rate < 0:
            raise CalculatorValidationError(f"{label}: interest rate cannot be negative.")
        if tenure is None or tenure <= 0:
            raise CalculatorValidationError(f"{label}: tenure must be a positive number of months.")

        emi = emi_amount(principal, rate, tenure)
        total_repaid = emi * tenure
        total_interest = total_repaid - principal

        results.append({
            "label": label,
            "principal": principal,
            "annual_interest_rate_pct": rate,
            "tenure_months": tenure,
            "emi": round(emi, 2),
            "total_interest_paid": round(total_interest, 2),
            "total_amount_repaid": round(total_repaid, 2),
        })

    lowest = min(results, key=lambda r: r["total_interest_paid"])
    return {
        "offers": results,
        "lowest_total_interest_offer": lowest["label"],
    }


# ---------------------------------------------------------------------------
# 4c. Opportunity Cost Calculator
# ---------------------------------------------------------------------------

def calculate_opportunity_cost(
    lump_sum_amount: float,
    loan_interest_rate_pct: float,
    investment_expected_return_pct: float,
    time_horizon_months: int,
) -> dict:
    if lump_sum_amount <= 0:
        raise CalculatorValidationError("Lump sum amount must be positive.")
    if loan_interest_rate_pct < 0:
        raise CalculatorValidationError("Loan interest rate cannot be negative.")
    if investment_expected_return_pct < 0:
        raise CalculatorValidationError("Expected investment return cannot be negative.")
    if time_horizon_months <= 0:
        raise CalculatorValidationError("Time horizon must be a positive number of months.")

    # Guaranteed savings from prepayment. Paying down a reducing-balance loan
    # is financially equivalent to a risk-free investment compounding at the
    # loan's own rate: every rupee of principal you avoid also avoids the
    # interest that would have accrued on it in every subsequent period, so
    # the correctly compounded (not simple-interest) avoided-interest amount
    # is lump_sum * [(1+r)^n - 1] -- the same compounding methodology used
    # for the investment side below, so the two are a valid apples-to-apples
    # comparison rather than simple-interest-vs-compound-interest.
    monthly_loan_rate = loan_interest_rate_pct / 12 / 100
    if monthly_loan_rate == 0:
        prepayment_interest_saved = 0.0
    else:
        prepayment_interest_saved = lump_sum_amount * ((1 + monthly_loan_rate) ** time_horizon_months - 1)

    # Projected (uncertain) investment growth over the same horizon, using
    # the standard compound-interest future value formula.
    monthly_investment_rate = investment_expected_return_pct / 12 / 100
    if monthly_investment_rate == 0:
        investment_future_value = lump_sum_amount
    else:
        investment_future_value = lump_sum_amount * (1 + monthly_investment_rate) ** time_horizon_months
    investment_growth = investment_future_value - lump_sum_amount

    return {
        "prepayment_option": {
            "label": "Prepay Loan",
            "guaranteed_interest_saved": round(prepayment_interest_saved, 2),
            "risk": "none (guaranteed)",
        },
        "investment_option": {
            "label": "Invest Instead",
            "projected_future_value": round(investment_future_value, 2),
            "projected_growth": round(investment_growth, 2),
            "risk": "market risk (not guaranteed)",
        },
        "comparison": {
            "projected_advantage_of_investing": round(investment_growth - prepayment_interest_saved, 2),
        },
    }
