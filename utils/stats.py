"""
stats.py
Financial risk and performance calculations.
"""

import numpy as np


def compute_stats(data, risk_free_rate=0.0):
    """
    Computes total return, annualized volatility, Sharpe ratio,
    and max drawdown from a price DataFrame with a 'Close' column.
    """
    returns = data["Close"].pct_change().dropna()

    total_return = (data["Close"].iloc[-1] / data["Close"].iloc[0]) - 1
    annualized_vol = returns.std() * np.sqrt(252)

    mean_daily_return = returns.mean()
    sharpe = 0.0
    if returns.std() != 0:
        sharpe = (mean_daily_return * 252 - risk_free_rate) / (returns.std() * np.sqrt(252))

    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    return {
        "total_return": total_return,
        "annualized_vol": annualized_vol,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "returns": returns,
    }


def add_moving_averages(data, ma_short, ma_long):
    """
    Returns a copy of data with two rolling moving average columns added.
    """
    data = data.copy()
    data[f"MA{ma_short}"] = data["Close"].rolling(ma_short).mean()
    data[f"MA{ma_long}"] = data["Close"].rolling(ma_long).mean()
    return data