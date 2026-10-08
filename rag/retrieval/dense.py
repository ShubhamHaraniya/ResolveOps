"""
Dense Vector Retrieval for ResolveOps RAG Policy Engine.
Executes semantic vector similarity search against the Qdrant index.
"""
from typing import List, Dict, Any, Optional
import structlog
from qdrant_client import QdrantClient

from rag.embeddings.embedder import get_embedder
from rag.ingestion.indexer import (
    get_qdrant_client,
    index_all_policy_chunks,
    COLLECTION_NAME,
)

log = structlog.get_logger()


def search_dense(
    query: str,
    top_k: int = 15,
    client: Optional[QdrantClient] = None,
) -> List[Dict[str, Any]]:
    """
    Perform dense vector search against indexed policy chunks.
    Returns sorted candidates with similarity scores.
    """
    if client is None:
        client, _ = index_all_policy_chunks()

    embedder = get_embedder()
    query_vector = embedder.embed_query(query)

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )

        candidates = []
        for point in results.points:
            payload = dict(point.payload or {})
            payload["dense_score"] = round(float(point.score), 4)
            candidates.append(payload)

        return candidates
    except Exception as e:
        log.warning("rag.retrieval.dense_search_failed", error=str(e))
        return []
