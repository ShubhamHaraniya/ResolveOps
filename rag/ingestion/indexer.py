"""
Dual-Mode Qdrant Indexer for ResolveOps RAG Policy Engine.
Connects to remote Qdrant if reachable; otherwise falls back gracefully
to an embedded/in-memory instance so local testing runs without Docker.
"""
from pathlib import Path
from typing import List, Optional
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from rag.ingestion.chunker import PolicyChunk, chunk_all_documents
from rag.embeddings.embedder import get_embedder, DEFAULT_DIM

log = structlog.get_logger()

COLLECTION_NAME = "resolveops_policies"

_qdrant_client: Optional[QdrantClient] = None
_indexed_chunks: List[PolicyChunk] = []


def get_qdrant_client(url: str = "http://localhost:6333") -> QdrantClient:
    """Return a cached or newly connected Qdrant client."""
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client

    # Attempt connection to remote Qdrant with short timeout
    try:
        client = QdrantClient(url=url, timeout=1.5, check_compatibility=False)
        client.get_collections()
        log.info("rag.qdrant.connected_remote", url=url)
        _qdrant_client = client
        return _qdrant_client
    except Exception as e:
        log.info("rag.qdrant.fallback_memory", reason=str(e))
        _qdrant_client = QdrantClient(":memory:")
        return _qdrant_client


def initialize_collection(client: QdrantClient, dim: int = DEFAULT_DIM) -> None:
    """Ensure the policy collection exists with proper vector parameters."""
    try:
        if not client.collection_exists(COLLECTION_NAME):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            log.info("rag.qdrant.collection_created", collection=COLLECTION_NAME, dim=dim)
    except Exception as e:
        log.warning("rag.qdrant.init_collection_failed", error=str(e))


def index_all_policy_chunks(
    docs_dir: Optional[Path] = None,
    client: Optional[QdrantClient] = None,
    force_reindex: bool = False,
) -> tuple[QdrantClient, List[PolicyChunk]]:
    """
    Parse all markdown policies, generate FastEmbed vectors, and index in Qdrant.
    """
    global _indexed_chunks
    if client is None:
        client = get_qdrant_client()

    initialize_collection(client)

    if _indexed_chunks and not force_reindex:
        return client, _indexed_chunks

    if docs_dir is None:
        docs_dir = Path(__file__).resolve().parents[1] / "documents"

    chunks = chunk_all_documents(docs_dir)
    if not chunks:
        log.warning("rag.qdrant.no_chunks_found", docs_dir=str(docs_dir))
        return client, []

    embedder = get_embedder()
    texts = [c.content for c in chunks]
    embeddings = embedder.embed_texts(texts)

    points = []
    for idx, (chunk, vec) in enumerate(zip(chunks, embeddings)):
        points.append(
            PointStruct(
                id=idx + 1,
                vector=vec,
                payload=chunk.to_dict(),
            )
        )

    try:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        _indexed_chunks = chunks
        log.info("rag.qdrant.indexed_success", count=len(points))
    except Exception as e:
        log.error("rag.qdrant.upsert_failed", error=str(e))

    return client, chunks


def get_indexed_chunks() -> List[PolicyChunk]:
    """Return all currently indexed PolicyChunk objects."""
    global _indexed_chunks
    if not _indexed_chunks:
        index_all_policy_chunks()
    return _indexed_chunks
