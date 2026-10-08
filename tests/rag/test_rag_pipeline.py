"""
Comprehensive Unit & Integration Test Suite for ResolveOps RAG Pipeline.
Verifies all M4 deliverables:
- FastEmbed embedder
- Dual-mode Qdrant indexer
- BM25 lexical retriever
- Reciprocal Rank Fusion (RRF)
- FlashRank reranker
- Contradictory policy precedence & conflict detection
- MCP KB tool execution
- LangGraph gather_context node integration
"""
import pytest
from pathlib import Path
from rag.embeddings.embedder import get_embedder
from rag.ingestion.indexer import index_all_policy_chunks, get_qdrant_client
from rag.retrieval.dense import search_dense
from rag.retrieval.bm25 import search_bm25
from rag.retrieval.hybrid import search_hybrid_candidates
from rag.reranking.reranker import rerank_candidates, detect_policy_conflicts
from rag.service import search_policies
from services.mcp_kb.server import list_tools, call_tool


@pytest.fixture(scope="module", autouse=True)
def setup_rag():
    """Ensure all documents are indexed before running tests."""
    client, chunks = index_all_policy_chunks(force_reindex=True)
    assert len(chunks) >= 50, "At least 50 policy chunks should be indexed"
    return client, chunks


def test_embedder_dimensions():
    embedder = get_embedder()
    vec = embedder.embed_query("Test query for Northwind Cloud policy")
    assert len(vec) == 384, "Embedding vector length should be 384"
    assert any(x != 0.0 for x in vec), "Vector should not be all zeros"


def test_dense_search_finds_relevant_policy():
    hits = search_dense("what is the refund limit for support agents?", top_k=5)
    assert len(hits) > 0, "Dense search should return candidates"
    # Should find refund policy
    doc_ids = [h["document_id"] for h in hits]
    assert any("refund" in did for did in doc_ids)


def test_bm25_exact_token_match():
    # Test exact rule code
    hits = search_bm25("REF-001 $50", top_k=5)
    assert len(hits) > 0
    # Should rank refund-policy-v3 highly because REF-001 and $50 are in it
    top_doc = hits[0]["document_id"]
    assert "refund-policy" in top_doc


def test_bm25_role_match():
    hits = search_bm25("viewer member prod-admin", top_k=5)
    assert len(hits) > 0
    doc_ids = [h["document_id"] for h in hits]
    assert "access-policy" in doc_ids


def test_hybrid_rrf_fusion():
    candidates = search_hybrid_candidates("duplicate charge refund", top_fused=5)
    assert len(candidates) == 5
    for c in candidates:
        assert "rrf_score" in c
        assert c["rrf_score"] > 0.0


def test_flashrank_reranker_and_conflict_detection():
    query = "I want a $40 refund for duplicate charge"
    candidates = search_hybrid_candidates(query, top_fused=10)
    top_chunks, conflict_info = rerank_candidates(query, candidates, top_n=4)

    assert len(top_chunks) <= 4
    # Active policy should take precedence over deprecated
    top_chunk = top_chunks[0]
    assert top_chunk["status"] == "active"
    assert top_chunk["document_id"] == "refund-policy-v3"

    # Verify conflict detected if v2 was in candidate pool
    has_v2 = any(c["document_id"] == "refund-policy-v2" for c in candidates)
    if has_v2:
        assert conflict_info["conflict_detected"] is True
        assert len(conflict_info["conflicts"]) > 0


def test_unified_rag_service():
    result = search_policies("Can I add seats mid-cycle?", category="subscription")
    assert "results" in result
    assert len(result["results"]) > 0
    # Should retrieve proration-policy or seat-policy
    doc_ids = [r["document_id"] for r in result["results"]]
    assert any(x in doc_ids for x in ["proration-policy", "seat-policy", "plan-policy"])


def test_mcp_kb_server():
    tools = list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "search_policy"
    assert tools[0]["annotations"]["readOnlyHint"] is True

    import asyncio
    res = asyncio.run(call_tool("search_policy", {"query": "how to reset MFA?", "category": "access"}))
    assert "results" in res
    doc_ids = [r["document_id"] for r in res["results"]]
    assert "mfa-policy" in doc_ids


def test_langgraph_gather_context_integration():
    import asyncio
    from backend.app.graph.nodes.gather_context import gather_context_node

    mock_state = {
        "ticket_id": "TKT-TEST-999",
        "raw_ticket": {
            "id": "TKT-TEST-999",
            "account_id": "ACC-001",
            "subject": "Duplicate charge on invoice, please refund $30",
            "body": "I was billed twice. Please refund $30 immediately.",
            "requester_email": "jane@acme.com",
        },
        "classification": {"category": "refund", "urgency": "medium"},
        "identity": {"verified": True, "method": "email_match", "confidence": 0.98},
        "total_tool_calls": 0,
    }

    result = asyncio.run(gather_context_node(mock_state))
    assert "context" in result
    ctx = result["context"]
    assert "rag_results" in ctx
    assert len(ctx["rag_results"]) > 0
    assert "policy_conflict" in ctx
    # Ensure active policy is top citation
    top_citation = ctx["rag_results"][0]
    assert top_citation["document_id"] == "refund-policy-v3"
    assert top_citation["status"] == "active"
