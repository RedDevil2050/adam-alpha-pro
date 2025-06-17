import numpy as np
from typing import Dict, List, Tuple


def calculate_wacc(
    beta: float,
    market_premium: float,
    risk_free_rate: float,
    debt_ratio: float,
    cost_of_debt: float,
    tax_rate: float,
) -> float:
    """Calculate Weighted Average Cost of Capital"""
    cost_of_equity = risk_free_rate + beta * market_premium
    after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)
    equity_ratio = 1 - debt_ratio
    return equity_ratio * cost_of_equity + debt_ratio * after_tax_cost_of_debt


def estimate_sustainable_growth(roe: float, retention_ratio: float) -> float:
    """Estimate sustainable growth rate using ROE and retention ratio"""
    return roe * retention_ratio


def calculate_relative_valuation_metrics(
    price: float,
    eps: float,
    book_value: float,
    sales: float,
    sector_medians: Dict[str, float],
) -> Dict[str, float]:
    """Calculate and compare multiple valuation metrics to sector medians"""
    metrics = {
        "pe_ratio": price / eps if eps > 0 else float("inf"),
        "pb_ratio": price / book_value if book_value > 0 else float("inf"),
        "ps_ratio": price / sales if sales > 0 else float("inf"),
    }

    relative_valuations = {
        k: metrics[k] / sector_medians[k] if k in sector_medians else 1.0
        for k in metrics
    }

    return relative_valuations


def run_scenario_analysis(
    base_value: float, scenarios: List[Dict]
) -> Tuple[float, Dict]:
    """Run scenario analysis with probability-weighted outcomes"""
    weighted_values = []
    for scenario in scenarios:
        adjusted_value = base_value * (1 + scenario["adjustment"])
        weighted_values.append(adjusted_value * scenario["probability"])

    expected_value = sum(weighted_values)
    return expected_value
