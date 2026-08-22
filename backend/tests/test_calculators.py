import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.calculators import (
    CalculatorValidationError,
    calculate_emi_comparison,
    calculate_opportunity_cost,
    calculate_sip_pause_vs_loan_payoff,
    emi_amount,
    sip_future_value,
)


def test_sip_future_value_zero_return_is_linear():
    assert sip_future_value(1000, 0, 12) == 12000


def test_sip_future_value_positive_return_grows():
    fv = sip_future_value(1000, 12, 12)
    assert fv > 12000


def test_emi_amount_known_value():
    # 100000 principal, 12% annual, 12 months -> EMI ~ 8884.88
    emi = emi_amount(100000, 12, 12)
    assert math.isclose(emi, 8884.88, rel_tol=1e-3)


def test_emi_amount_zero_rate():
    assert emi_amount(12000, 0, 12) == 1000


def test_sip_pause_vs_loan_payoff_reduces_interest():
    result = calculate_sip_pause_vs_loan_payoff(
        monthly_sip_amount=5000,
        expected_annual_return_pct=10,
        loan_outstanding_amount=500000,
        loan_interest_rate_pct=10,
        loan_remaining_tenure_months=36,
        pause_duration_months=6,
    )
    assert result["comparison"]["loan_interest_saved"] > 0
    assert result["comparison"]["loan_tenure_reduced_months"] >= 0
    assert result["scenario_b"]["loan_total_interest"] < result["scenario_a"]["loan_total_interest"]


def test_sip_pause_rejects_pause_longer_than_tenure():
    with pytest.raises(CalculatorValidationError):
        calculate_sip_pause_vs_loan_payoff(
            monthly_sip_amount=5000,
            expected_annual_return_pct=10,
            loan_outstanding_amount=500000,
            loan_interest_rate_pct=10,
            loan_remaining_tenure_months=12,
            pause_duration_months=24,
        )


def test_sip_pause_rejects_negative_rate():
    with pytest.raises(CalculatorValidationError):
        calculate_sip_pause_vs_loan_payoff(
            monthly_sip_amount=5000,
            expected_annual_return_pct=10,
            loan_outstanding_amount=500000,
            loan_interest_rate_pct=-5,
            loan_remaining_tenure_months=12,
            pause_duration_months=3,
        )


def test_emi_comparison_picks_lowest_interest_offer():
    result = calculate_emi_comparison([
        {"label": "Bank A", "principal": 500000, "annual_interest_rate_pct": 9, "tenure_months": 60},
        {"label": "Bank B", "principal": 500000, "annual_interest_rate_pct": 11, "tenure_months": 60},
    ])
    assert result["lowest_total_interest_offer"] == "Bank A"
    assert len(result["offers"]) == 2


def test_emi_comparison_requires_two_offers():
    with pytest.raises(CalculatorValidationError):
        calculate_emi_comparison([
            {"label": "Bank A", "principal": 500000, "annual_interest_rate_pct": 9, "tenure_months": 60},
        ])


def test_opportunity_cost_flags_guaranteed_vs_projected():
    result = calculate_opportunity_cost(
        lump_sum_amount=200000,
        loan_interest_rate_pct=9,
        investment_expected_return_pct=12,
        time_horizon_months=24,
    )
    assert result["prepayment_option"]["risk"] == "none (guaranteed)"
    assert "not guaranteed" in result["investment_option"]["risk"]
    assert result["investment_option"]["projected_growth"] > 0


def test_opportunity_cost_prepayment_uses_compound_not_simple_interest():
    """Both sides of the comparison must use the same (compound) methodology
    -- comparing simple-interest loan savings against compound investment
    growth would be an invalid, misleading comparison."""
    result = calculate_opportunity_cost(
        lump_sum_amount=200000,
        loan_interest_rate_pct=9,
        investment_expected_return_pct=12,
        time_horizon_months=24,
    )
    monthly_rate = 9 / 12 / 100
    simple_interest_estimate = 200000 * monthly_rate * 24
    compound_interest = result["prepayment_option"]["guaranteed_interest_saved"]
    assert compound_interest > simple_interest_estimate
    assert math.isclose(compound_interest, 39282.71, rel_tol=1e-3)


def test_opportunity_cost_rejects_negative_return():
    with pytest.raises(CalculatorValidationError):
        calculate_opportunity_cost(
            lump_sum_amount=200000,
            loan_interest_rate_pct=9,
            investment_expected_return_pct=-1,
            time_horizon_months=24,
        )


def test_calculator_module_has_no_llm_imports():
    """Code-review checkpoint from the spec: the calculator module must not
    import any LLM/API client."""
    source = Path(__file__).resolve().parents[1].joinpath("app", "calculators.py").read_text()
    forbidden = ["openai", "anthropic", "langchain", "requests", "httpx"]
    lowered = source.lower()
    for term in forbidden:
        assert term not in lowered, f"calculators.py must not reference {term}"
