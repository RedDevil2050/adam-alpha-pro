import pandas as pd

def calculate_metrics(equity_curve):
    df = pd.DataFrame(equity_curve)
    df['returns'] = df['value'].pct_change().fillna(0)
    df['cum_max'] = df['value'].cummax()
    df['drawdown'] = (df['value'] - df['cum_max']) / df['cum_max']
    sharpe_ratio = df['returns'].mean() / df['returns'].std() * sqrt(252) if df['returns'].std() > 0 else 0
    max_drawdown = df['drawdown'].min()
    return round(sharpe_ratio, 2), round(max_drawdown * 100, 2)

def apply_strategy(verdicts: list, capital: float = 100000.0) -> dict:
    equity_curve = []
    cash = capital
    shares = 0
    last_price = 0

    for entry in verdicts:
        price = entry['price']
        verdict = entry['verdict']

        if verdict == 'BUY' and cash > 0:
            shares = cash / price
            cash = 0
        elif verdict == 'SELL' and shares > 0:
            cash = shares * price
            shares = 0

        portfolio_value = cash + shares * price
        equity_curve.append({'date': entry['date'], 'value': round(portfolio_value, 2)})
        last_price = price

    final_value = cash + shares * last_price
    sharpe, max_dd = calculate_metrics(equity_curve)

    return {
        'final_value': round(final_value, 2),
        'equity_curve': equity_curve,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd
    }
