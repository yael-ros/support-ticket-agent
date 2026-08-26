"""Unit tests for knowledge_base/embeddings.py — no live API calls.

Mirrors test_gemini_provider.py's pattern: swap in a fake client so
tenacity's real retry/backoff logic runs against it, rather than mocking
tenacity itself.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from support_agent.knowledge_base import embeddings


@pytest.fixture(autouse=True)
def _reset_client_cache():
    embeddings._client = None
    yield
    embeddings._client = None


def _fake_embedding_response(values_list: list[list[float]]):
    return MagicMock(embeddings=[MagicMock(values=values) for values in values_list])


def test_missing_api_key_raises_clear_error():
    with (
        patch.dict("os.environ", {}, clear=True),
        pytest.raises(RuntimeError, match="GEMINI_API_KEY"),
    ):
        embeddings._get_client()


def test_embed_texts_returns_vectors():
    fake_client = MagicMock()
    fake_client.models.embed_content.return_value = _fake_embedding_response(
        [[0.1, 0.2], [0.3, 0.4]]
    )

    with patch.object(embeddings, "_get_client", return_value=fake_client):
        result = embeddings.embed_texts(["a", "b"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    fake_client.models.embed_content.assert_called_once_with(
        model=embeddings.EMBEDDING_MODEL_NAME, contents=["a", "b"]
    )


def test_embed_texts_retries_transient_errors_then_succeeds():
    fake_client = MagicMock()
    fake_client.models.embed_content.side_effect = [
        genai_errors.APIError(code=503, response_json={"message": "unavailable"}),
        genai_errors.APIError(code=429, response_json={"message": "rate limited"}),
        _fake_embedding_response([[0.5, 0.6]]),
    ]

    with patch.object(embeddings, "_get_client", return_value=fake_client):
        result = embeddings.embed_texts(["a"])

    assert result == [[0.5, 0.6]]
    assert fake_client.models.embed_content.call_count == 3


def test_embed_texts_raises_after_exhausting_retries():
    fake_client = MagicMock()
    fake_client.models.embed_content.side_effect = genai_errors.APIError(
        code=503, response_json={"message": "unavailable"}
    )

    with (
        patch.object(embeddings, "_get_client", return_value=fake_client),
        pytest.raises(RuntimeError, match=f"failed after {embeddings.MAX_RETRIES} attempts"),
    ):
        embeddings.embed_texts(["a"])

    assert fake_client.models.embed_content.call_count == embeddings.MAX_RETRIES


def test_embed_texts_does_not_retry_non_retryable_errors():
    fake_client = MagicMock()
    fake_client.models.embed_content.side_effect = genai_errors.APIError(
        code=400, response_json={"message": "bad request"}
    )

    with (
        patch.object(embeddings, "_get_client", return_value=fake_client),
        pytest.raises(RuntimeError, match="Embedding call failed: "),
    ):
        embeddings.embed_texts(["a"])

    assert fake_client.models.embed_content.call_count == 1


def test_embed_texts_raises_when_response_has_no_embeddings():
    fake_client = MagicMock()
    fake_client.models.embed_content.return_value = MagicMock(embeddings=None)

    with (
        patch.object(embeddings, "_get_client", return_value=fake_client),
        pytest.raises(RuntimeError, match="no embeddings"),
    ):
        embeddings.embed_texts(["a"])
