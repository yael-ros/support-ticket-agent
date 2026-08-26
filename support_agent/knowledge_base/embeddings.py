"""The single embedding entry point used by both build_index.py and retriever.py.

Calls Gemini's hosted embedding API (client.models.embed_content) rather
than loading a local model. Originally this was a local
sentence-transformers/all-MiniLM-L6-v2 model — swapped out specifically
to fix a Render free-tier deployment crashing with "Out of memory (used
over 512Mi)": importing sentence-transformers alone (it pulls in torch)
cost ~261MB of process RSS, plus another ~40MB the moment the model
weights actually loaded on first use, measured directly against this
app's real import chain. See HANDOFF.md's Ops section for the full
before/after.

ASSUMPTION: this now requires a GEMINI_API_KEY unconditionally, even when
LLM_PROVIDER=anthropic for classify/draft — retrieval (every ticket goes
through it) always calls Gemini's embedding endpoint regardless of which
provider is configured for text generation. This is a new, real coupling
introduced by this swap; previously the app could run on Anthropic alone
with no Gemini key at all.

Model: gemini-embedding-001 (3072-dim output), chosen over the
gemini-embedding-2 / gemini-embedding-2-preview alternatives available to
this API key (confirmed live via client.models.list()) as the longest-
established, non-preview GA embedding model — this project has previously
observed newer/preview Gemini models carrying a *smaller* free-tier quota
than older stable ones (see gemini_provider.py's MODEL_BY_TIER docstring),
so "newest" isn't assumed to be "best" here without evidence either way.

Retry policy mirrors gemini_provider.py's (retry 429/5xx with backoff,
don't retry anything else) — duplicated rather than imported from there,
since embeddings.py is deliberately standalone (nothing in build_index.py
or retriever.py depends on how it's implemented internally) and pulling
in agent.providers would create a backwards dependency (agent already
depends on knowledge_base via agent/nodes/retrieve.py).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

# Loads a repo-root .env file (gitignored) if present, without overriding
# any key already set in the real environment. A no-op if no .env file
# exists — safe to call unconditionally at import time.
load_dotenv()

EMBEDDING_MODEL_NAME = "gemini-embedding-001"

MAX_RETRIES = 5
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        # Explicit check rather than letting genai.Client() hit its own
        # generic "Missing key inputs argument!" ValueError — this needs
        # to fail loudly and specifically here, since build_index.py now
        # calls embed_texts() at deploy *build* time (see its module
        # docstring): a vague SDK error at that point is much harder to
        # diagnose than "GEMINI_API_KEY is not set" pointing straight at
        # a missing Render build-time env var.
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Set it as an environment variable "
                "(or in a gitignored .env file) before building the KB index "
                "or making retrieval calls."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _is_retryable(exc: BaseException) -> bool:
    return (
        isinstance(exc, genai_errors.APIError)
        and getattr(exc, "code", None) in _RETRYABLE_STATUS_CODES
    )


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _embed(texts: list[str]):
    return _get_client().models.embed_content(model=EMBEDDING_MODEL_NAME, contents=texts)


def embed_texts(texts: list[str]) -> list[list[float]]:
    try:
        response = _embed(texts)
    except genai_errors.APIError as exc:
        if _is_retryable(exc):
            raise RuntimeError(
                f"Embedding call failed after {MAX_RETRIES} attempts: {exc}"
            ) from exc
        raise RuntimeError(f"Embedding call failed: {exc}") from exc

    if response.embeddings is None:
        raise RuntimeError(f"Embedding call returned no embeddings. Response: {response!r}")

    return [embedding.values for embedding in response.embeddings]
