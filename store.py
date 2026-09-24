"""In-memory ChromaDB store for document chunks, using Chroma's default embedding function."""

import uuid

import chromadb

from ingest import Chunk


def build_collection(chunks: list[Chunk]) -> chromadb.Collection:
    """Embed chunks into a fresh in-memory collection, with id, page and source as metadata."""
    client = chromadb.EphemeralClient()
    collection = client.create_collection(
        name=f"chunks_{uuid.uuid4().hex}",
        metadata={"hnsw:space": "cosine"},
    )
    if not chunks:
        return collection

    metadatas = []
    for c in chunks:
        meta: dict[str, str | int] = {"id": c.id, "source": c.source}
        if c.page is not None:  # Chroma rejects None metadata values
            meta["page"] = c.page
        metadatas.append(meta)

    collection.add(
        ids=[c.id for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=metadatas,
    )
    return collection


def search(collection: chromadb.Collection, query: str, k: int = 4) -> list[dict]:
    """Return the top k chunks for `query` as dicts with id, page, source, text and score.

    score is cosine similarity (higher is better, 1.0 is identical).
    """
    k = min(k, collection.count())
    if k <= 0:
        return []
    res = collection.query(query_texts=[query], n_results=k)
    return [
        {
            "id": meta["id"],
            "page": meta.get("page"),
            "source": meta["source"],
            "text": doc,
            "score": 1.0 - dist,
        }
        for meta, doc, dist in zip(
            res["metadatas"][0], res["documents"][0], res["distances"][0]
        )
    ]
