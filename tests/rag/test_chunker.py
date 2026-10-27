"""
Tests for section-aware markdown chunker in rag/ingestion/chunker.py
"""
from pathlib import Path
from rag.ingestion.chunker import chunk_document, chunk_all_documents


def test_chunk_refund_policy_v3():
    doc_path = Path("rag/documents/refund-policy-v3.md")
    assert doc_path.exists(), "refund-policy-v3.md should exist"

    chunks = chunk_document(doc_path)
    assert len(chunks) >= 4, "Should create multiple chunks for sections"

    # Check that metadata was correctly extracted
    for chunk in chunks:
        assert chunk.document_id == "refund-policy-v3"
        assert chunk.version == 3
        assert chunk.status == "active"
        assert chunk.effective_date == "2025-01-01"
        assert len(chunk.content) > 40


def test_chunk_deprecated_refund_v2():
    doc_path = Path("rag/documents/refund-policy-v2.md")
    assert doc_path.exists()

    chunks = chunk_document(doc_path)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.status == "deprecated"
        assert chunk.version == 2
        assert chunk.superseded_by == "refund-policy-v3"


def test_chunk_all_18_documents():
    docs_dir = Path("rag/documents")
    all_chunks = chunk_all_documents(docs_dir)

    # 18 documents should yield at least 50 chunks
    assert len(all_chunks) >= 50

    doc_ids = {c.document_id for c in all_chunks}
    assert "refund-policy-v1" in doc_ids
    assert "refund-policy-v2" in doc_ids
    assert "refund-policy-v3" in doc_ids
    assert "plan-policy" in doc_ids
    assert "proration-policy" in doc_ids
    assert "seat-policy" in doc_ids
    assert "access-policy" in doc_ids
    assert "mfa-policy" in doc_ids
    assert "escalation-policy" in doc_ids
    assert "tone-guidelines" in doc_ids
    assert "billing-policy" in doc_ids
    assert "invoice-policy" in doc_ids
    assert "strategic-account-policy" in doc_ids
    assert "legal-hold-policy.md" not in doc_ids
    assert "legal-hold-policy" in doc_ids
    assert "credit-policy" in doc_ids
    assert "chargeback-policy" in doc_ids
    assert "data-privacy-policy" in doc_ids
    assert "security-incident-policy" in doc_ids
