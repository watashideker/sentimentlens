import pytest

from ingest import Chunk
from store import build_collection, search


@pytest.fixture(scope="module")
def chunks():
    return [
        Chunk(id="a.pdf:p1:c0", text="The battery life is excellent and lasts all day.", page=1, source="a.pdf"),
        Chunk(id="a.pdf:p2:c0", text="Customer support was slow and unhelpful when I called.", page=2, source="a.pdf"),
        Chunk(id="b.txt:c0", text="The screen is bright and the colors look vivid.", page=None, source="b.txt"),
    ]


@pytest.fixture(scope="module")
def collection(chunks):
    return build_collection(chunks)


def test_build_collection_stores_metadata(collection):
    assert collection.count() == 3
    got = collection.get(ids=["a.pdf:p2:c0"])
    assert got["metadatas"][0] == {"id": "a.pdf:p2:c0", "page": 2, "source": "a.pdf"}
    assert got["documents"][0].startswith("Customer support")


def test_search_returns_best_match_first(collection):
    results = search(collection, "how long does the battery last?", k=2)
    assert len(results) == 2
    assert results[0]["id"] == "a.pdf:p1:c0"
    assert results[0]["page"] == 1
    assert results[0]["source"] == "a.pdf"
    assert results[0]["score"] >= results[1]["score"]
    assert -1.0 <= results[0]["score"] <= 1.0


def test_search_page_none_for_pageless_chunks(collection):
    results = search(collection, "bright vivid display", k=1)
    assert results[0]["id"] == "b.txt:c0"
    assert results[0]["page"] is None


def test_search_k_larger_than_collection(collection):
    assert len(search(collection, "anything", k=10)) == 3


def test_empty_collection():
    empty = build_collection([])
    assert search(empty, "hello", k=3) == []


def test_collections_are_independent(chunks):
    one = build_collection(chunks[:1])
    two = build_collection(chunks[1:])
    assert one.count() == 1
    assert two.count() == 2
