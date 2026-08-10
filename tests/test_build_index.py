from support_agent.knowledge_base.build_index import (
    CHUNK_MAX_TOKENS,
    _approx_tokens,
    chunk_document,
)
from support_agent.schemas import Category, KBDocument


def _doc(body: str) -> KBDocument:
    return KBDocument(
        id="test-doc",
        title="Test Document",
        category=Category.GENERAL_INQUIRY,
        body=body,
        source_note="test fixture",
    )


def test_short_document_produces_a_single_chunk():
    doc = _doc("This is a short paragraph.\n\nAnd a second short paragraph.")
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].doc_id == "test-doc"
    assert "short paragraph" in chunks[0].text


def test_long_document_splits_into_multiple_chunks_with_overlap():
    # Each paragraph is ~110 tokens; 5 paragraphs exceeds CHUNK_MAX_TOKENS
    # comfortably, forcing a split.
    paragraph = "word " * 85  # ~85 words ≈ 110 approx-tokens
    body = "\n\n".join(f"{paragraph.strip()} marker{i}" for i in range(5))
    doc = _doc(body)

    chunks = chunk_document(doc)
    assert len(chunks) > 1

    # chunk_index is sequential starting at 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    # No chunk wildly exceeds the token budget (allowing one paragraph's
    # worth of slack since packing only checks *before* adding a paragraph).
    for chunk in chunks:
        assert _approx_tokens(chunk.text) <= CHUNK_MAX_TOKENS + 150

    # Overlap: the paragraph at the end of chunk N should reappear at the
    # start of chunk N+1.
    for i in range(len(chunks) - 1):
        last_para_of_current = chunks[i].text.split("\n\n")[-1]
        assert last_para_of_current in chunks[i + 1].text


def test_all_documents_chunk_without_error():
    from support_agent.knowledge_base.documents import DOCUMENTS

    for doc in DOCUMENTS:
        chunks = chunk_document(doc)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.doc_id == doc.id
            assert chunk.category == doc.category
            assert chunk.text.strip()
