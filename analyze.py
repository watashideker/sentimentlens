"""Topic-level sentiment analysis and grounded Q&A over a document collection, using Claude."""

import json
import os
from typing import Literal

import anthropic
import chromadb
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

import store

load_dotenv()

TOPICS = [
    "overall outlook",
    "revenue and growth",
    "costs and margins",
    "risks",
    "guidance",
]
TOP_K = 4
MAX_TOKENS = 2000
NEUTRAL_BAND = 0.25  # |overall score| at or below this is reported as neutral

Sentiment = Literal["positive", "neutral", "negative"]


class ConfigError(RuntimeError):
    """Raised when required configuration (API key, model) is missing."""


class AnalysisError(RuntimeError):
    """Raised when Claude's response cannot be parsed after a retry."""


class Quote(BaseModel):
    text: str
    chunk_id: str


class TopicResult(BaseModel):
    topic: str
    sentiment: Sentiment
    score: float = Field(ge=-1, le=1)
    reason: str
    quotes: list[Quote] = Field(default_factory=list, max_length=3)


class DocumentResult(BaseModel):
    overall_sentiment: Sentiment
    overall_score: float = Field(ge=-1, le=1)
    topics: list[TopicResult]
    total_input_tokens: int
    total_output_tokens: int


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file or environment."
        )
    return anthropic.Anthropic(api_key=api_key)


def _get_model() -> str:
    model = os.environ.get("CLAUDE_MODEL", "").strip()
    if not model:
        raise ConfigError(
            "CLAUDE_MODEL is not set. Add it to your .env file or environment."
        )
    return model


def _format_chunks(chunks: list[dict]) -> str:
    return "\n\n".join(f'<chunk id="{c["id"]}">\n{c["text"]}\n</chunk>' for c in chunks)


def _call(client: anthropic.Anthropic, model: str, prompt: str) -> tuple[str, int, int]:
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    return text, response.usage.input_tokens, response.usage.output_tokens


def _extract_json(text: str) -> dict:
    """Parse a JSON object from `text`, tolerating markdown fences or surrounding prose."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("no JSON object found in response")
    return json.loads(text[start : end + 1])


def _topic_prompt(topic: str, chunks: list[dict]) -> str:
    return f"""You are analyzing sentiment in a document. Using ONLY the excerpts below, assess the sentiment toward this topic: "{topic}".

{_format_chunks(chunks)}

Respond with a single JSON object and nothing else (no markdown, no commentary), in exactly this shape:
{{
  "topic": "{topic}",
  "sentiment": "positive" | "neutral" | "negative",
  "score": <number from -1 (most negative) to 1 (most positive)>,
  "reason": "<one sentence explaining the sentiment>",
  "quotes": [{{"text": "<verbatim quote from an excerpt>", "chunk_id": "<id of the chunk it came from>"}}]
}}

Rules:
- Include at most 3 quotes, each copied verbatim from the excerpts, with the chunk_id of its chunk.
- If the excerpts say little about the topic, use "neutral", a score near 0, and an empty quotes list."""


def _analyze_topic(
    client: anthropic.Anthropic, model: str, topic: str, chunks: list[dict]
) -> tuple[TopicResult, int, int]:
    """Ask Claude about one topic; retry once if the response fails to parse or validate."""
    prompt = _topic_prompt(topic, chunks)
    tokens_in = tokens_out = 0
    last_error: Exception | None = None
    for _ in range(2):
        text, t_in, t_out = _call(client, model, prompt)
        tokens_in += t_in
        tokens_out += t_out
        try:
            result = TopicResult.model_validate(_extract_json(text))
            return result, tokens_in, tokens_out
        except (ValueError, ValidationError) as e:  # JSONDecodeError is a ValueError
            last_error = e
    raise AnalysisError(f"Could not parse a valid response for topic '{topic}': {last_error}")


def analyze_document(collection: chromadb.Collection) -> DocumentResult:
    """Score sentiment for each topic in TOPICS and combine into a DocumentResult."""
    if collection.count() == 0:
        raise ValueError("The document has no content to analyze.")
    client = _get_client()
    model = _get_model()

    results: list[TopicResult] = []
    total_in = total_out = 0
    for topic in TOPICS:
        chunks = store.search(collection, topic, k=TOP_K)
        result, t_in, t_out = _analyze_topic(client, model, topic, chunks)
        results.append(result)
        total_in += t_in
        total_out += t_out

    overall = sum(r.score for r in results) / len(results)
    if overall > NEUTRAL_BAND:
        sentiment: Sentiment = "positive"
    elif overall < -NEUTRAL_BAND:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    return DocumentResult(
        overall_sentiment=sentiment,
        overall_score=overall,
        topics=results,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
    )


def answer_question(collection: chromadb.Collection, question: str) -> str:
    """Answer `question` using only the top retrieved chunks, citing chunk ids."""
    client = _get_client()
    model = _get_model()
    chunks = store.search(collection, question, k=TOP_K)
    if not chunks:
        return "The answer is not in the document."

    prompt = f"""Answer the question using ONLY the excerpts below. Do not use outside knowledge.
Cite the chunk ids you relied on in square brackets after each claim, e.g. [report.pdf:p2:c0].
If the excerpts do not contain the answer, say clearly that the answer is not in the document.

{_format_chunks(chunks)}

Question: {question}"""
    text, _, _ = _call(client, model, prompt)
    return text.strip()
