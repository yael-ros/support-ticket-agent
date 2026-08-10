"""Query the knowledge base's Chroma collection for relevant chunks.

Assumes `build_index.py` has already been run and `CHROMA_DIR` contains a
populated collection named `COLLECTION_NAME` — if the collection doesn't
exist, `retrieve()` raises rather than silently returning an empty list,
per CLAUDE.md's "no silent failures" rule (an agent node seeing zero
chunks because the index was never built is a very different situation
from a query that legitimately has no good match, and callers need to be
able to tell those apart).

Embedding goes through the same `embed_texts()` used at index-build time
(knowledge_base/embeddings.py) — a query embedded with a different model
than the one used to build the index would produce meaningless similarity
scores, so both paths deliberately share one function.
"""

from __future__ import annotations

from pathlib import Path

import chromadb

from support_agent.knowledge_base.build_index import CHROMA_DIR, COLLECTION_NAME
from support_agent.knowledge_base.embeddings import embed_texts
from support_agent.schemas import Category, RetrievedChunk


def _get_collection(persist_dir: Path = CHROMA_DIR):
    client = chromadb.PersistentClient(path=str(persist_dir))
    existing = {c.name for c in client.list_collections()}
    if COLLECTION_NAME not in existing:
        raise RuntimeError(
            f"Chroma collection '{COLLECTION_NAME}' not found at {persist_dir}. "
            "Run `python -m support_agent.knowledge_base.build_index` first."
        )
    return client.get_collection(COLLECTION_NAME)


def retrieve(
    query: str, k: int = 5, *, category: Category | None = None, persist_dir: Path = CHROMA_DIR
) -> list[RetrievedChunk]:
    """Return the top-`k` chunks most similar to `query`, ranked by similarity (highest first).

    `score` is cosine similarity in [-1, 1] (the collection is created with
    `hnsw:space="cosine"` in build_index.py), higher is more similar.

    If `category` is given, restricts the search to chunks from documents
    in that category — used by the agent's retrieve node once a ticket has
    been classified, to avoid cross-category noise (e.g. a billing query
    pulling in an IT_SUPPORT chunk).
    """
    collection = _get_collection(persist_dir)
    query_embedding = embed_texts([query])
    where = {"category": category.value} if category is not None else None

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for chunk_id, text, meta, distance in zip(ids, documents, metadatas, distances):
        # Collection uses hnsw:space="cosine", so Chroma's distance is
        # exactly (1 - cosine_similarity).
        similarity = 1 - distance
        chunks.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                doc_id=meta["doc_id"],
                doc_title=meta["doc_title"],
                category=Category(meta["category"]),
                text=text,
                score=similarity,
            )
        )

    return chunks
