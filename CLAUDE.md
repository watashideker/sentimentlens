# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FinLens is a Streamlit app with two tools behind a shared router and theme:

- **SentimentLens**: upload a PDF/DOCX/TXT, get topic-level sentiment from Claude, and ask grounded questions (RAG over an in-memory ChromaDB collection).
- **StockLens**: pull price history via `yfinance`, with moving averages, risk stats and Plotly charts.

## Setup

- Python virtualenv lives in `.venv/` (activate with `source .venv/bin/activate`).
- Install deps: `pip install -r requirements.txt`
- Configuration is read from `.env`, which defines `ANTHROPIC_API_KEY` and `CLAUDE_MODEL`. Loaded with `python-dotenv`; never print or commit its values.

## Commands

- Run app: `streamlit run app.py`
- Run tests: `pytest` (`pytest.ini` sets `pythonpath = .` and `testpaths = tests`); single test: `pytest tests/test_analyze.py::test_name`
- Tests cover the SentimentLens backend only (`ingest`, `store`, `analyze`). There is no UI test suite; to check that pages load, use `streamlit.testing.v1.AppTest.from_file(<absolute path to app.py>)`, then `switch_page("views/<page>.py")` and `run()`, and assert `at.exception` is empty. Use an absolute path, since relative paths resolve against the calling file.

## Layout

```
app.py                 Router: st.navigation (top nav), page config, injects CSS + particles.js
views/home.py          Hero and the two tool cards
views/sentimentlens.py SentimentLens page (upload, analyze, chat)
views/stocklens.py     StockLens page (sidebar settings, metrics, charts)
utils/ui.py            Module icons (ICONS, icon_badge) and title_card()
utils/data.py          yfinance price loading
utils/stats.py         Returns, volatility, Sharpe, drawdown, moving averages
utils/charts.py        Plotly figures
ingest.py              File to text to overlapping chunks (800 chars, 100 overlap)
store.py               In-memory ChromaDB collection from chunks
analyze.py             Claude calls: topic sentiment and grounded Q&A
assets/style.css       All styling and colors (CSS variables)
assets/logo.svg        Line-mark logo, emerald to blue gradient
assets/particles.js    Background particle canvas
.streamlit/config.toml Dark theme base (primary color emerald)
tests/                 pytest tests for ingest, store, analyze
```

## App structure

- `app.py` reads `assets/style.css`, strips comments and whitespace to one line, and injects it with `st.markdown` (a blank line would end the HTML block, and `st.html` strips `<style>`). Keep `style.css` valid when minified: no `//` comments.
- `app.py` calls `st.set_page_config` after `st.navigation` so it can open the sidebar expanded only on StockLens (`pg.title == "StockLens"`).
- Nav icons use `:material/...:` names. The same names live in `utils/ui.py` `ICONS`, so change icons in both places.
- Each module page wraps its content in `st.container(key="canvas_sentiment")` or `"canvas_stock"` and starts with `title_card(...)`. Home cards are containers keyed `card_sentiment` and `card_stock` inside `tool_grid`.

## Styling conventions

- Every color is a CSS variable in `assets/style.css`. Do not hardcode colors in views; charts are the exception where Plotly/Vega inline colors are overridden from CSS with `!important`.
- Module identity: `--accent`, `--accent-rgb` and `--accent-ink` default to emerald (Home). The `st-key-canvas_*` and `st-key-card_*` classes, and `.stApp:has(.st-key-canvas_*)`, swap them: SentimentLens violet `#8B5CF6`, StockLens cyan `#22D3EE`. A new module needs a variable pair, a canvas key and matching selector entries.
- Icons are Material Symbols Rounded (imported in `style.css`), same size and weight everywhere, shown in `.fl-badge` squares tinted with the accent.
- Home cards: the whole card is clickable via an `st.page_link` stretched over it with CSS at zero opacity; the two cards share a CSS grid so they stay equal height and stack on mobile.
- Sentiment badge colors (green/grey/red) are semantic and intentionally not tied to the accent.
