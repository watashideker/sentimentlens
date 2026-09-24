import base64
from pathlib import Path

import streamlit as st

from utils.ui import icon_badge

logo_b64 = base64.b64encode((Path(__file__).parent.parent / "assets" / "logo.svg").read_bytes()).decode()

HERO_CHART = (
    '<svg class="finlens-hero-chart" viewBox="0 0 800 260" preserveAspectRatio="none" aria-hidden="true">'
    '<defs><linearGradient id="fl-line" x1="0" x2="1"><stop offset="0" stop-color="#10B981"/>'
    '<stop offset="1" stop-color="#3B82F6"/></linearGradient>'
    '<linearGradient id="fl-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#10B981" stop-opacity="0.18"/>'
    '<stop offset="1" stop-color="#10B981" stop-opacity="0"/></linearGradient></defs>'
    '<path d="M0 220 L70 195 L130 205 L200 160 L270 175 L340 125 L410 140 L480 95 L550 110 L620 60 L700 75 L800 25 L800 260 L0 260 Z" fill="url(#fl-fill)"/>'
    '<path d="M0 220 L70 195 L130 205 L200 160 L270 175 L340 125 L410 140 L480 95 L550 110 L620 60 L700 75 L800 25" '
    'fill="none" stroke="url(#fl-line)" stroke-width="2" opacity="0.45" vector-effect="non-scaling-stroke"/></svg>'
)

st.markdown(
    f"""
    <div class="finlens-hero">
      {HERO_CHART}
      <img src="data:image/svg+xml;base64,{logo_b64}" width="88" alt="FinLens logo">
      <h1 class="finlens-title">FinLens</h1>
      <p class="finlens-tagline">Two lenses on finance.<br><span>Read the <em>mood</em> of a document.</span> <span>Trace the <em>story</em> of a stock.</span></p>
    </div>
    """,
    unsafe_allow_html=True,
)

TOOLS = [
    ("sentiment", "SentimentLens", "Upload a document to know its sentiment", "views/sentimentlens.py"),
    ("stock", "StockLens", "Price history, moving averages and risk stats for any ticker", "views/stocklens.py"),
]

# Each card is one HTML body plus a page_link that CSS stretches over the whole card
with st.container(key="tool_grid"):
    for module, name, blurb, page in TOOLS:
        with st.container(key=f"card_{module}"):
            st.markdown(
                f'<div class="fl-card-body">{icon_badge(module)}<div class="fl-card-name">{name}</div>'
                f'<p class="fl-card-desc">{blurb}</p>'
                f'<div class="fl-card-open">Open {name}<span class="material-symbols-rounded">arrow_forward</span></div></div>',
                unsafe_allow_html=True,
            )
            st.page_link(page, label=f"Open {name}")
