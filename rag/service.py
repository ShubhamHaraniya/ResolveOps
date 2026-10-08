"""
Unified RAG Policy Service for ResolveOps.
Exposes high-level search_policies API combining dense retrieval, BM25,
Reciprocal Rank Fusion, FlashRank neural reranking, and policy conflict resolution.
"""
from typing import List, Dict, Any, Optional
import structlog

from rag.retrieval.hybrid import search_hybrid_candidates
from rag.reranking.reranker import rerank_candidates

log = structlog.get_logger()


def search_policies(
    query: str,
    category: Optional[str] = None,
    top_k: int = 4,
) -> Dict[str, Any]:
    """
    Search policy corpus using full hybrid RAG pipeline:
    1. Dense (Qdrant) + BM25 (rank_bm25) retrieval
    2. Reciprocal Rank Fusion (RRF) candidate merge
    3. FlashRank neural reranking
    4. Active-first precedence & contradictory conflict detection
    """
    search_query = query
    if category and category.lower() not in query.lower():
        search_query = f"{category} {query}"

    # Step 1 & 2: Dense + BM25 + RRF
    candidates = search_hybrid_candidates(query=search_query, top_fused=20)

    # Step 3 & 4: FlashRank + Conflict Detection + Active-First Sorting
    top_chunks, conflict_info = rerank_candidates(
        query=search_query,
        candidates=candidates,
        top_n=top_k,
    )

    # Format structured citations for LangGraph and UI
    citations = []
    for c in top_chunks:
        citations.append({
            "chunk_id": c.get("chunk_id"),
            "document_id": c.get("document_id"),
            "title": c.get("title"),
            "version": c.get("version"),
            "section": c.get("section"),
            "subsection": c.get("subsection"),
            "status": c.get("status"),
            "effective_date": c.get("effective_date"),
            "content": c.get("content"),
            "relevance_score": c.get("rerank_score", 0.0),
            "source_file": c.get("source_file"),
        })

    return {
        "query": query,
        "category": category,
        "results": citations,
        "conflict_detected": conflict_info.get("conflict_detected", False),
        "conflicts": conflict_info.get("conflicts", []),
    }
