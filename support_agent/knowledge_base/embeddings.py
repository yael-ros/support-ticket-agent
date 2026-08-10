"""The single embedding entry point used by both build_index.py and retriever.py.

Local `sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU-friendly) —
keeps this project runnable without API cost, per BUILD_PLAN.md. To swap
in a hosted embedding API (e.g. Voyage AI, OpenAI text-embedding-3) for
production scale, reimplement `embed_texts()` to call that API instead —
nothing in build_index.py or retriever.py depends on how it's implemented
internally, only on "list[str] in, list[list[float]] out".
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _get_model().encode(texts, show_progress_bar=False).tolist()
