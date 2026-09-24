import streamlit as st
from datetime import date, timedelta

from utils.data import load_price_data
from utils.stats import compute_stats, add_moving_averages
from utils.charts import price_ma_chart, returns_histogram, normalized_comparison_chart
from utils.ui import title_card

canvas = st.container(key="canvas_stock")
with canvas:
    title_card("stock", "StockLens", "Enter a ticker to pull price history, moving averages, and risk stats.")


# ---------- Sidebar inputs ----------
with st.sidebar:
    st.header("Settings")
    ticker = st.text_input("Ticker symbol", value="AAPL").upper().strip()

    compare_mode = st.checkbox("Compare with another ticker")
    ticker2 = ""
    if compare_mode:
        ticker2 = st.text_input("Compare against", value="MSFT").upper().strip()

    default_start = date.today() - timedelta(days=5 * 365)
    start_date = st.date_input(
        "Start date", value=default_start,
        min_value=date(1990, 1, 1), max_value=date.today()
    )
    end_date = st.date_input(
        "End date", value=date.today(),
        min_value=date(1990, 1, 1), max_value=date.today()
    )

    ma_short = st.number_input("Short moving average (days)", min_value=5, max_value=100, value=50)
    ma_long = st.number_input("Long moving average (days)", min_value=50, max_value=400, value=200)

    run = st.button("Load Data", type="primary")


def render_ticker_panel(ticker, data, ma_short, ma_long):
    """Renders metrics, price+MA chart, and returns histogram for one ticker."""
    data = add_moving_averages(data, ma_short, ma_long)
    stats = compute_stats(data)

    st.subheader(ticker)

    m1, m2 = st.columns(2)
    m1.metric("Total Return", f"{stats['total_return']*100:.1f}%")
    m2.metric("Sharpe Ratio", f"{stats['sharpe']:.2f}")
    m3, m4 = st.columns(2)
    m3.metric("Ann. Volatility", f"{stats['annualized_vol']*100:.1f}%")
    m4.metric("Max Drawdown", f"{stats['max_drawdown']*100:.1f}%")

    st.plotly_chart(price_ma_chart(data, ma_short, ma_long), use_container_width=True)
    st.subheader("Daily Returns Distribution")
    st.plotly_chart(returns_histogram(stats["returns"]), use_container_width=True)

    return data


# ---------- Main logic ----------
with canvas:
    if run:
        if not ticker:
            st.warning("Enter a ticker symbol to continue.")
        else:
            tickers_to_load = [ticker]
            if compare_mode and ticker2:
                tickers_to_load.append(ticker2)

            with st.spinner("Pulling data..."):
                loaded = {t: load_price_data(t, start_date, end_date) for t in tickers_to_load}

            missing = [t for t, d in loaded.items() if d is None or len(d) < ma_long]
            if missing:
                st.error(
                    f"Not enough data for: {', '.join(missing)}. "
                    "Check the symbol, or widen the date range."
                )
            else:
                if compare_mode and ticker2:
                    st.subheader("Normalized Comparison (rebased to 100)")
                    st.plotly_chart(normalized_comparison_chart(loaded), use_container_width=True)
                    st.divider()

                    col1, col2 = st.columns(2)
                    with col1:
                        render_ticker_panel(ticker, loaded[ticker], ma_short, ma_long)
                    with col2:
                        render_ticker_panel(ticker2, loaded[ticker2], ma_short, ma_long)
                else:
                    render_ticker_panel(ticker, loaded[ticker], ma_short, ma_long)
    else:
        st.info("Set your ticker(s) and date range in the sidebar, then click **Load Data**.")