"""SentimentLens: upload a document, get topic-level sentiment, and chat with it."""

import hashlib
import os

import anthropic
import pandas as pd
import streamlit as st

import analyze
import ingest
import store

st.set_page_config(page_title="SentimentLens", page_icon="🔍", layout="centered")

BADGE_COLORS = {"positive": "#2e9e5b", "neutral": "#8a8f98", "negative": "#d64545"}
PLACEHOLDER_HINTS = ("your", "here", "xxxx", "changeme", "placeholder", "<", "...")


def api_key_problem() -> str | None:
    """Return a friendly message if the API key is missing or still a placeholder."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return "No Anthropic API key found. Add `ANTHROPIC_API_KEY` to your `.env` file and restart the app."
    if any(h in key.lower() for h in PLACEHOLDER_HINTS):
        return "`ANTHROPIC_API_KEY` in your `.env` file still looks like a placeholder. Replace it with a real key and restart the app."
    return None


def show_api_error(exc: Exception) -> None:
    """Translate expected failures into a friendly st.error instead of a traceback."""
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        st.error("The Anthropic API rejected your API key. Check `ANTHROPIC_API_KEY` in your `.env` file.")
    elif isinstance(exc, anthropic.NotFoundError):
        st.error("The API could not find the configured model. Check `CLAUDE_MODEL` in your `.env` file.")
    elif isinstance(exc, anthropic.RateLimitError):
        st.error("Rate limit reached. Please wait a moment and try again.")
    elif isinstance(exc, anthropic.APIConnectionError):
        st.error("Could not reach the Anthropic API. Check your internet connection and try again.")
    elif isinstance(exc, (analyze.ConfigError, analyze.AnalysisError, ValueError)):
        st.error(str(exc))
    elif isinstance(exc, anthropic.APIError):
        st.error(f"The Anthropic API returned an error: {exc.message}")
    else:
        raise exc


def load_document(uploaded) -> dict | None:
    """Ingest and index the upload once; return its cached state, keyed by file name."""
    data = uploaded.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    docs = st.session_state.setdefault("docs", {})

    # A new upload resets everything: drop any other file's state.
    for name in [n for n in docs if n != uploaded.name]:
        del docs[name]

    doc = docs.get(uploaded.name)
    if doc is None or doc["digest"] != digest:
        try:
            with st.spinner("Reading and indexing document..."):
                chunks = ingest.ingest_file(data, uploaded.name)
                collection = store.build_collection(chunks)
        except ValueError as e:
            st.error(str(e))
            return None
        doc = {
            "digest": digest,
            "chunks": {c.id: c for c in chunks},
            "collection": collection,
            "result": None,
            "chat": [],
        }
        docs[uploaded.name] = doc
    return doc


def render_result(result: analyze.DocumentResult) -> None:
    color = BADGE_COLORS[result.overall_sentiment]
    st.markdown(
        f"""<div style="background:{color};color:white;border-radius:14px;padding:1.2rem;
        text-align:center;margin:0.5rem 0 1rem">
        <div style="font-size:2.4rem;font-weight:700;letter-spacing:0.05em">
        {result.overall_sentiment.upper()}</div>
        <div style="font-size:1.1rem;opacity:0.9">Score: {result.overall_score:+.2f}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.subheader("Topic scores")
    df = pd.DataFrame(
        {"Score": [t.score for t in result.topics]},
        index=pd.Index([t.topic.title() for t in result.topics], name="Topic"),
    )
    st.bar_chart(df, y="Score")

    for t in result.topics:
        with st.expander(f"{t.topic.title()} — {t.sentiment} ({t.score:+.2f})"):
            st.write(t.reason)
            if not t.quotes:
                st.caption("No supporting quotes.")
            for q in t.quotes:
                st.markdown(f"> {q.text}")
                st.caption(citation_label(q.chunk_id))


def citation_label(chunk_id: str) -> str:
    doc = current_doc()
    chunk = doc["chunks"].get(chunk_id) if doc else None
    if chunk is None:
        return f"Chunk `{chunk_id}`"
    page = f", page {chunk.page}" if chunk.page else ""
    return f"Chunk `{chunk_id}`{page}"


def cited_chunks(answer: str, chunks: dict) -> list[str]:
    """Chunk ids from the document that the answer mentions, in order of appearance."""
    found = [(answer.find(cid), cid) for cid in chunks if cid in answer]
    return [cid for _, cid in sorted(found)]


def current_doc() -> dict | None:
    return st.session_state.get("current")


def render_chat_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("cited"):
            with st.expander("Cited chunks"):
                for cid in msg["cited"]:
                    chunk = current_doc()["chunks"][cid]
                    st.caption(citation_label(cid))
                    st.text(chunk.text)


st.title("SentimentLens")
st.caption("Upload a document to know its sentiment")

uploaded = st.file_uploader("Document", type=["pdf", "docx", "txt"], label_visibility="collapsed")

if uploaded is None:
    st.session_state.pop("docs", None)
    st.session_state.pop("current", None)
    st.stop()

doc = load_document(uploaded)
if doc is None:
    st.stop()
st.session_state["current"] = doc

st.success(f"**{uploaded.name}** — {len(doc['chunks'])} chunks")

problem = api_key_problem()
if problem:
    st.error(problem)

if st.button("Analyze", type="primary", disabled=problem is not None):
    try:
        with st.spinner("Analyzing sentiment..."):
            doc["result"] = analyze.analyze_document(doc["collection"])
    except Exception as e:
        show_api_error(e)

if doc["result"]:
    render_result(doc["result"])

st.divider()
st.subheader("Ask about the document")

for msg in doc["chat"]:
    render_chat_message(msg)

question = st.chat_input("Ask a question about this document", disabled=problem is not None)
if question:
    user_msg = {"role": "user", "content": question}
    doc["chat"].append(user_msg)
    render_chat_message(user_msg)
    try:
        with st.spinner("Thinking..."):
            answer = analyze.answer_question(doc["collection"], question)
        reply = {
            "role": "assistant",
            "content": answer,
            "cited": cited_chunks(answer, doc["chunks"]),
        }
        doc["chat"].append(reply)
        render_chat_message(reply)
    except Exception as e:
        doc["chat"].pop()  # don't keep an unanswered question in the history
        show_api_error(e)
