"""
FlashRank Neural Reranker & Policy Conflict Engine for ResolveOps.
Reranks fused candidates to the top 3-5 high-precision policy chunks.
Detects contradictory active vs deprecated rules (e.g., refund-policy-v2 vs v3),
enforces active precedence, and surfaces conflict metadata for LLM and UI.
"""
from typing import List, Dict, Any, Optional
import structlog
from flashrank import Ranker, RerankRequest

log = structlog.get_logger()

_ranker_instance: Optional[Ranker] = None


def get_ranker() -> Ranker:
    """Return the shared FlashRank ranker instance."""
    global _ranker_instance
    if _ranker_instance is None:
        try:
            _ranker_instance = Ranker()
            log.info("rag.reranker.ready", model="ms-marco-TinyBERT-L-2-v2")
        except Exception as e:
            log.warning("rag.reranker.init_failed", error=str(e))
            _ranker_instance = None
    return _ranker_instance


def detect_policy_conflicts(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect contradictory policies in candidate pool.
    Example: refund-policy-v2 (deprecated, $100 threshold) vs
             refund-policy-v3 (active, $50 threshold).
    """
    active_docs = {c["document_id"] for c in candidates if c.get("status") == "active"}
    deprecated_docs = {
        c["document_id"]: c.get("superseded_by")
        for c in candidates
        if c.get("status") == "deprecated"
    }

    conflict_detected = False
    conflict_details = []

    for dep_id, superseder in deprecated_docs.items():
        # Check if the active superseder document is also present in candidates
        if superseder and superseder in active_docs:
            conflict_detected = True
            conflict_details.append({
                "deprecated_document": dep_id,
                "active_document": superseder,
                "resolution": f"Active policy '{superseder}' supersedes deprecated '{dep_id}'. Rule from '{superseder}' takes precedence.",
            })

    return {
        "conflict_detected": conflict_detected,
        "conflicts": conflict_details,
    }


def rerank_candidates(
    query: str,
    candidates: List[Dict[str, Any]],
    top_n: int = 5,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Rerank candidates using FlashRank, apply active-first precedence,
    and return the top 3-5 policy chunks alongside conflict diagnostics.
    """
    if not candidates:
        return [], {"conflict_detected": False, "conflicts": []}

    conflict_info = detect_policy_conflicts(candidates)
    ranker = get_ranker()

    if ranker is not None:
        try:
            passages = [
                {"id": idx, "text": c.get("content", "")}
                for idx, c in enumerate(candidates)
            ]
            rerank_req = RerankRequest(query=query, passages=passages)
            ranked_results = ranker.rerank(rerank_req)

            # Map scores back to candidate dicts
            for r in ranked_results:
                orig_idx = r["id"]
                score = float(r.get("score", 0.0))
                candidates[orig_idx]["rerank_score"] = round(score, 4)
        except Exception as e:
            log.warning("rag.reranker.rerank_error", error=str(e))
            for c in candidates:
                c["rerank_score"] = c.get("rrf_score", 0.0)
    else:
        for c in candidates:
            c["rerank_score"] = c.get("rrf_score", 0.0)

    # Sort with active-first precedence:
    # 1. status == 'active' comes before 'deprecated'
    # 2. higher rerank_score comes first
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (
            1 if c.get("status") == "active" else 0,
            c.get("rerank_score", 0.0),
        ),
        reverse=True,
    )

    final_chunks = sorted_candidates[:top_n]

    log.info(
        "rag.reranker.complete",
        query=query[:40],
        input_count=len(candidates),
        output_count=len(final_chunks),
        conflict=conflict_info["conflict_detected"],
    )

    return final_chunks, conflict_info
