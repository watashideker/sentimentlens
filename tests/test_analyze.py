import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import analyze
from analyze import AnalysisError, ConfigError, DocumentResult, TopicResult


def fake_response(text, tokens_in=10, tokens_out=5):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=tokens_in, output_tokens=tokens_out),
    )


def topic_json(topic="x", sentiment="positive", score=0.5, quotes=None):
    return json.dumps(
        {
            "topic": topic,
            "sentiment": sentiment,
            "score": score,
            "reason": "Because.",
            "quotes": quotes if quotes is not None else [{"text": "good", "chunk_id": "a:c0"}],
        }
    )


@pytest.fixture
def client(monkeypatch):
    c = MagicMock()
    monkeypatch.setattr(analyze, "_get_client", lambda: c)
    monkeypatch.setenv("CLAUDE_MODEL", "test-model")
    monkeypatch.setattr(
        analyze.store,
        "search",
        lambda coll, q, k=4: [{"id": "a:c0", "text": "Revenue grew.", "page": 1, "source": "a", "score": 0.9}],
    )
    return c


@pytest.fixture
def collection():
    c = MagicMock()
    c.count.return_value = 3
    return c


def test_missing_api_key_raises(monkeypatch, collection):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        analyze.analyze_document(collection)
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        analyze.answer_question(collection, "q?")


def test_analyze_document_aggregates(client, collection):
    scores = [0.8, 0.4, -0.2, -0.6, 0.2]
    client.messages.create.side_effect = [
        fake_response(topic_json(topic=t, score=s, sentiment="neutral"), 100, 20)
        for t, s in zip(analyze.TOPICS, scores)
    ]
    result = analyze.analyze_document(collection)

    assert isinstance(result, DocumentResult)
    assert [t.topic for t in result.topics] == analyze.TOPICS
    assert result.overall_score == pytest.approx(sum(scores) / 5)
    assert result.overall_sentiment == "neutral"
    assert result.total_input_tokens == 500
    assert result.total_output_tokens == 100
    assert client.messages.create.call_args.kwargs["model"] == "test-model"


def test_overall_sentiment_thresholds(client, collection):
    client.messages.create.side_effect = [
        fake_response(topic_json(score=0.9)) for _ in analyze.TOPICS
    ]
    assert analyze.analyze_document(collection).overall_sentiment == "positive"
    client.messages.create.side_effect = [
        fake_response(topic_json(sentiment="negative", score=-0.9)) for _ in analyze.TOPICS
    ]
    assert analyze.analyze_document(collection).overall_sentiment == "negative"


def test_parses_fenced_json(client, collection):
    fenced = f"```json\n{topic_json()}\n```"
    client.messages.create.side_effect = [fake_response(fenced) for _ in analyze.TOPICS]
    assert analyze.analyze_document(collection).topics[0].quotes[0].chunk_id == "a:c0"


def test_retries_once_on_bad_json_and_counts_tokens(client, collection):
    responses = [fake_response("not json", 7, 3), fake_response(topic_json(), 10, 5)]
    responses += [fake_response(topic_json()) for _ in analyze.TOPICS[1:]]
    client.messages.create.side_effect = responses
    result = analyze.analyze_document(collection)
    assert client.messages.create.call_count == len(analyze.TOPICS) + 1
    assert result.total_input_tokens == 7 + 10 + 10 * 4
    assert result.total_output_tokens == 3 + 5 + 5 * 4


def test_retries_on_schema_violation_then_fails(client, collection):
    client.messages.create.return_value = fake_response(topic_json(score=5))
    with pytest.raises(AnalysisError, match="overall outlook"):
        analyze.analyze_document(collection)
    assert client.messages.create.call_count == 2  # one retry, then give up


def test_topic_result_limits():
    base = {"topic": "t", "sentiment": "positive", "score": 0.1, "reason": "r"}
    quotes = [{"text": "q", "chunk_id": "c"}] * 4
    with pytest.raises(ValueError):
        TopicResult(**base, quotes=quotes)
    with pytest.raises(ValueError):
        TopicResult(**{**base, "sentiment": "happy"})


def test_empty_collection_rejected(client):
    empty = MagicMock()
    empty.count.return_value = 0
    with pytest.raises(ValueError):
        analyze.analyze_document(empty)


def test_answer_question_uses_chunks_and_returns_text(client, collection):
    client.messages.create.return_value = fake_response("  Revenue grew [a:c0].  ")
    answer = analyze.answer_question(collection, "How did revenue do?")
    assert answer == "Revenue grew [a:c0]."
    prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert 'id="a:c0"' in prompt and "Revenue grew." in prompt
    assert "How did revenue do?" in prompt
    assert "not in the document" in prompt


def test_answer_question_no_chunks_skips_api(client, collection, monkeypatch):
    monkeypatch.setattr(analyze.store, "search", lambda *a, **k: [])
    assert "not in the document" in analyze.answer_question(collection, "q?")
    client.messages.create.assert_not_called()
