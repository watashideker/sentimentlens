"""FinLens: router for the SentimentLens and StockLens tools."""

import re
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="FinLens", page_icon="assets/logo.svg", layout="wide")

pages = [
    st.Page("views/home.py", title="Home", icon="🏠", default=True),
    st.Page("views/sentimentlens.py", title="SentimentLens", icon="🔍"),
    st.Page("views/stocklens.py", title="StockLens", icon="📈"),
]
pg = st.navigation(pages, position="top")

# Rendered before pg.run() as a fixed bar: a page calling st.stop() would
# otherwise block anything drawn after it. Styles load once here for every page.
assets = Path(__file__).parent / "assets"
# Minified to one line: st.markdown ends an HTML block at the first blank line,
# and st.html strips <style> contents, so neither can take the raw file.
css = re.sub(r"\s+", " ", re.sub(r"/\*.*?\*/", "", (assets / "style.css").read_text(), flags=re.S))
st.markdown(
    f'<style>{css}</style><div class="finlens-footer">Made with ♥ by Swapnil Pant · Built with Claude Code</div>',
    unsafe_allow_html=True,
)
st.html(f"<script>{(assets / 'particles.js').read_text()}</script>", unsafe_allow_javascript=True)

pg.run()
