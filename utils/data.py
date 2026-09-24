"""
data.py
Handles pulling and cleaning price data from external sources.
"""

import yfinance as yf


def load_price_data(ticker, start, end):
    """
    Downloads historical closing prices for a given ticker.
    Returns a DataFrame with a single 'Close' column, or None if no data found.
    """
    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        return None

    data = data[["Close"]].dropna()
    data.columns = ["Close"]
    return data