"""
Hybrid Retrieval with Reciprocal Rank Fusion (RRF) for ResolveOps.
Fuses Qdrant dense vector candidates with BM25 lexical candidates
to guarantee both semantic matching and exact rule/numeric retrieval.
"""
from typing import List, Dict, Any, Optional
import structlog

from rag.retrieval.dense import search_dense
from rag.retrieval.bm25 import search_bm25

log = structlog.get_logger()

RRF_K = 60  # Standard Reciprocal Rank Fusion smoothing parameter


def search_hybrid_candidates(
    query: str,
    top_dense: int = 15,
    top_bm25: int = 15,
    top_fused: int = 20,
) -> List[Dict[str, Any]]:
    """
    Execute dense vector search and BM25 lexical search, then fuse
    rankings using Reciprocal Rank Fusion (RRF).
    """
    dense_results = search_dense(query=query, top_k=top_dense)
    bm25_results = search_bm25(query=query, top_k=top_bm25)

    fused_scores: Dict[str, float] = {}
    chunk_store: Dict[str, Dict[str, Any]] = {}

    # Accumulate dense RRF scores
    for rank, item in enumerate(dense_results):
        cid = item["chunk_id"]
        chunk_store[cid] = item
        fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (RRF_K + rank + 1))

    # Accumulate BM25 RRF scores
    for rank, item in enumerate(bm25_results):
        cid = item["chunk_id"]
        if cid not in chunk_store:
            chunk_store[cid] = item
        else:
            # Preserve bm25_score on existing item
            chunk_store[cid]["bm25_score"] = item.get("bm25_score", 0.0)
        fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (RRF_K + rank + 1))

    # Sort combined candidates by fused RRF score descending
    sorted_chunks = sorted(
        fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True
    )

    fused_candidates: List[Dict[str, Any]] = []
    for cid in sorted_chunks[:top_fused]:
        item = dict(chunk_store[cid])
        item["rrf_score"] = round(fused_scores[cid], 5)
        fused_candidates.append(item)

    log.info(
        "rag.hybrid.fused",
        query=query[:40],
        dense_count=len(dense_results),
        bm25_count=len(bm25_results),
        fused_count=len(fused_candidates),
    )

    return fused_candidates
