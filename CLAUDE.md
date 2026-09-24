# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

The repo is currently a bare scaffold: only `requirements.txt`, `.env`, and a `.venv/` exist. There is no source code, README, tests, or git history yet. Update this file once code is added (entry point, module layout, real test/lint commands).

## Setup

- Python virtualenv lives in `.venv/` (activate with `source .venv/bin/activate`).
- Install deps: `pip install -r requirements.txt`
- Dependencies indicate the intended stack: `streamlit` (UI), `anthropic` (Claude API), `chromadb` (vector store), `pypdf` and `python-docx` (document ingestion), `pydantic` (data models/validation), `python-dotenv` (env loading), `pytest` (tests).
- Configuration is read from `.env`, which defines `ANTHROPIC_API_KEY` and `CLAUDE_MODEL`. Load it with `python-dotenv`; never print or commit its values.

## Commands (expected, once code exists)

- Run app: `streamlit run <entry_file>.py`
- Run tests: `pytest`; single test: `pytest path/to/test_file.py::test_name`
