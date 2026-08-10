"""Chunk, embed, and index the knowledge base into a local Chroma collection.

Chunking: paragraph-aware ("semantic" in the sense of never splitting mid-
paragraph) packing into ~200-400 token windows. Overlap is achieved by
always carrying the last paragraph of a closed chunk forward as the first
paragraph of the next one — simpler and more predictable than trying to
fill a fixed overlap token budget with however many trailing paragraphs
happen to fit (KB paragraphs are themselves often 50-120 tokens, so a
tight budget would frequently produce zero overlap). Token count is
approximated as `word_count * 1.3` — close enough for chunk-sizing
purposes without pulling in a tokenizer dependency; the embedding model's
own tokenizer handles the real tokenization downstream. Most of this KB's
40 articles (89-200 words) fit in a single chunk; the handful of longer
step-by-step articles (~250-300 words) split into 2 chunks, which is what
exercises the overlap logic.

Embedding: delegated to knowledge_base/embeddings.py — see that module's
docstring for the local-model choice and the production swap-out point.

Storage: Chroma, local file-backed persistent client — no external vector
DB service required to run this project. Persisted under
`support_agent/knowledge_base/chroma/` (gitignored).

Assumption: every document in `documents.py` has a non-empty body and a
valid `Category`; this module does no defensive validation of KB content
since, unlike the ticket dataset, the KB is entirely hand-authored and
under our own control.
"""

from __future__ import annotations

from pathlib import Path

import chromadb

from support_agent.knowledge_base.documents import DOCUMENTS
from support_agent.knowledge_base.embeddings import embed_texts
from support_agent.schemas import Chunk, KBDocument

CHROMA_DIR = Path(__file__).parent / "chroma"
COLLECTION_NAME = "kb_articles"

CHUNK_MAX_TOKENS = 350


def _approx_tokens(text: str) -> int:
    """Rough word-count-based token estimate (see module docstring)."""
    return int(len(text.split()) * 1.3)


def chunk_document(doc: KBDocument) -> list[Chunk]:
    """Split a KBDocument's body into paragraph-aware, overlapping chunks."""
    paragraphs = [p.strip() for p in doc.body.split("\n\n") if p.strip()]

    chunk_texts: list[str] = []
    current_paras: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _approx_tokens(para)

        if current_paras and current_tokens + para_tokens > CHUNK_MAX_TOKENS:
            chunk_texts.append("\n\n".join(current_paras))

            # Overlap: the last paragraph of the chunk just closed opens
            # the next one, so a claim near a chunk boundary always has
            # full context in at least one chunk.
            current_paras = [current_paras[-1]]
            current_tokens = _approx_tokens(current_paras[0])

        current_paras.append(para)
        current_tokens += para_tokens

    if current_paras:
        chunk_texts.append("\n\n".join(current_paras))

    return [
        Chunk(
            id=f"{doc.id}::chunk{i}",
            doc_id=doc.id,
            doc_title=doc.title,
            category=doc.category,
            chunk_index=i,
            text=text,
        )
        for i, text in enumerate(chunk_texts)
    ]


def chunk_all_documents(documents: list[KBDocument] = DOCUMENTS) -> list[Chunk]:
    chunks = [chunk for doc in documents for chunk in chunk_document(doc)]
    return chunks


def build_index(documents: list[KBDocument] = DOCUMENTS, persist_dir: Path = CHROMA_DIR) -> None:
    """Chunk every document, embed the chunks, and (re)write the Chroma collection."""
    chunks = chunk_all_documents(documents)
    embeddings = embed_texts([c.text for c in chunks])

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))

    # Rebuild from scratch each run so stale chunks from removed/edited
    # documents never linger in the index.
    existing = {c.name for c in client.list_collections()}
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
    # Explicit cosine space so retriever.py's similarity score is exactly
    # `1 - distance`, independent of whether embeddings happen to be
    # unit-normalized (they aren't, by default, from SentenceTransformer.encode).
    collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    collection.add(
        ids=[c.id for c in chunks],
        embeddings=embeddings,
        documents=[c.text for c in chunks],
        metadatas=[
            {
                "doc_id": c.doc_id,
                "doc_title": c.doc_title,
                "category": c.category.value,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ],
    )

    multi_chunk_docs = sum(1 for doc in documents if len(chunk_document(doc)) > 1)
    print(f"[build_index] Documents: {len(documents)}")
    print(f"[build_index] Chunks: {len(chunks)} ({multi_chunk_docs} documents split into >1 chunk)")
    print(f"[build_index] Indexed into Chroma collection '{COLLECTION_NAME}' at {persist_dir}")


if __name__ == "__main__":
    build_index()
