from support_agent.knowledge_base.documents import DOCUMENTS
from support_agent.schemas import Category


def test_at_least_30_documents():
    assert len(DOCUMENTS) >= 30


def test_document_ids_are_unique():
    ids = [doc.id for doc in DOCUMENTS]
    assert len(ids) == len(set(ids))


def test_every_category_has_at_least_one_document():
    covered = {doc.category for doc in DOCUMENTS}
    assert covered == set(Category)


def test_every_document_has_nonempty_body_and_source_note():
    for doc in DOCUMENTS:
        assert doc.body.strip()
        assert doc.source_note.strip()
