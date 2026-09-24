"""
charts.py
Builds Plotly figures used across the dashboard.
"""

import plotly.graph_objects as go


def price_ma_chart(data, ma_short, ma_long):
    """Line chart of closing price with two moving average overlays."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data["Close"], name="Close", line=dict(width=1.5)))
    fig.add_trace(go.Scatter(x=data.index, y=data[f"MA{ma_short}"], name=f"{ma_short}d MA", line=dict(width=1.1, dash="dot")))
    fig.add_trace(go.Scatter(x=data.index, y=data[f"MA{ma_long}"], name=f"{ma_long}d MA", line=dict(width=1.1, dash="dot")))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
    return fig


def returns_histogram(returns):
    """Histogram of daily returns."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=returns, nbinsx=50))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
    return fig


def normalized_comparison_chart(loaded_data):
    """
    Overlay chart comparing multiple tickers, each rebased to start at 100,
    so relative performance is comparable regardless of price scale.
    loaded_data: dict of {ticker_symbol: DataFrame}
    """
    fig = go.Figure()
    for ticker, data in loaded_data.items():
        normalized = data["Close"] / data["Close"].iloc[0] * 100
        fig.add_trace(go.Scatter(x=data.index, y=normalized, name=ticker))
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
    return fig