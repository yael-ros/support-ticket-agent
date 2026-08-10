from support_agent.knowledge_base.documents import DOCUMENTS
from support_agent.knowledge_base.retrieval_eval_set import RETRIEVAL_EVAL_SET


def test_at_least_20_eval_pairs():
    assert len(RETRIEVAL_EVAL_SET) >= 20


def test_every_expected_doc_id_exists_in_documents():
    real_ids = {doc.id for doc in DOCUMENTS}
    for query, expected_doc_id in RETRIEVAL_EVAL_SET:
        assert expected_doc_id in real_ids, (
            f"Eval query {query!r} references unknown doc_id {expected_doc_id!r}"
        )


def test_no_duplicate_queries():
    queries = [q for q, _ in RETRIEVAL_EVAL_SET]
    assert len(queries) == len(set(queries))
