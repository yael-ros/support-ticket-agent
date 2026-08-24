"""Integration test for the retriever against a small, isolated fixture index.

Builds a real (tiny) Chroma collection under a pytest tmp_path using the
real embedding model — this is deliberately not mocked, since the thing
being tested is actual semantic similarity ranking, which a mock would
trivially fake.

The ranking tests below are opt-in, gated behind RUN_LIVE_EMBEDDING_TESTS,
mirroring test_anthropic_provider_live.py's pattern: embeddings.py now
calls Gemini's hosted embedding API (see its module docstring) rather
than running a free local model, so exercising real ranking behavior
means a real, quota-consuming network call on every test run unless
opted in — every other test in this project mocks the API for exactly
this reason. test_retrieve_missing_index_raises stays unconditional: it
fails inside _get_collection() before retrieve() ever calls embed_texts(),
so it has no live dependency to gate.

    RUN_LIVE_EMBEDDING_TESTS=1 pytest tests/test_retriever.py

Requires a real GEMINI_API_KEY (via env var or a gitignored .env).
"""

from __future__ import annotations

import os

import pytest

from support_agent.knowledge_base.build_index import build_index
from support_agent.knowledge_base.retriever import retrieve
from support_agent.schemas import Category, KBDocument

_live_embeddings = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_EMBEDDING_TESTS") != "1",
    reason="opt-in live test — set RUN_LIVE_EMBEDDING_TESTS=1 (and a real GEMINI_API_KEY) to run it",
)

FIXTURE_DOCS = [
    KBDocument(
        id="fixture-password",
        title="Resetting your password",
        category=Category.IT_SUPPORT,
        body="Click 'Forgot password?' on the login screen and follow the emailed link to set a new password.",
        source_note="test fixture",
    ),
    KBDocument(
        id="fixture-refund",
        title="Requesting a refund",
        category=Category.RETURNS_AND_EXCHANGES,
        body="Refunds can be requested within 30 days of delivery from your order history page.",
        source_note="test fixture",
    ),
    KBDocument(
        id="fixture-outage",
        title="Checking service status",
        category=Category.SERVICE_OUTAGES_AND_MAINTENANCE,
        body="Visit the status page to see whether there is an ongoing outage affecting your account.",
        source_note="test fixture",
    ),
]


@pytest.fixture(scope="module")
def fixture_index(tmp_path_factory):
    persist_dir = tmp_path_factory.mktemp("chroma_fixture")
    build_index(documents=FIXTURE_DOCS, persist_dir=persist_dir)
    return persist_dir


@_live_embeddings
def test_retrieve_returns_ranked_chunks_with_expected_fields(fixture_index):
    results = retrieve("I forgot my password and can't log in", k=3, persist_dir=fixture_index)

    assert len(results) > 0
    top = results[0]
    assert top.doc_id == "fixture-password"
    assert -1.0 <= top.score <= 1.0
    # Ranked by descending similarity
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


@_live_embeddings
def test_retrieve_respects_category_filter(fixture_index):
    results = retrieve(
        "forgot password", k=3, category=Category.RETURNS_AND_EXCHANGES, persist_dir=fixture_index
    )
    assert all(r.category == Category.RETURNS_AND_EXCHANGES for r in results)
    assert all(r.doc_id != "fixture-password" for r in results)


def test_retrieve_missing_index_raises(tmp_path):
    with pytest.raises(RuntimeError, match="not found"):
        retrieve("anything", persist_dir=tmp_path / "does_not_exist")
