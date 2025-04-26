import numpy as np

def calculate_ev_ebitda_valuation(enterprise_value, ebitda, sector_median=12):
    """Enterprise Value to EBITDA valuation"""
    ev_ebitda = enterprise_value / ebitda if ebitda != 0 else float('inf')
    relative_value = sector_median / ev_ebitda if ev_ebitda != 0 else 0
    return {
        'ev_ebitda': ev_ebitda,
        'sector_relative': relative_value,
        'verdict': 'UNDERVALUED' if relative_value > 1.2 else 'OVERVALUED' if relative_value < 0.8 else 'FAIR'
    }

def calculate_graham_value(eps, book_value, growth_rate=0.0):
    """Graham's Number - Intrinsic Value Calculation"""
    return np.sqrt(22.5 * eps * (book_value + (7 * growth_rate)))

def calculate_dividend_discount(dividend, growth_rate, discount_rate):
    """Gordon Growth Model for Dividend Stocks"""
    if discount_rate <= growth_rate:
        return float('inf')
    return dividend * (1 + growth_rate) / (discount_rate - growth_rate)
