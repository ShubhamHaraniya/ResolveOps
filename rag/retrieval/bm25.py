"""
BM25 Lexical Retrieval for ResolveOps RAG Policy Engine.
Provides exact keyword and token matching for monetary values ($50, $100),
timeframes (30 days), roles (viewer, member), and policy codes (REF-001).
"""
import re
from typing import List, Dict, Any, Optional
import structlog
from rank_bm25 import BM25Okapi

from rag.ingestion.indexer import get_indexed_chunks
from rag.ingestion.chunker import PolicyChunk

log = structlog.get_logger()

_bm25_index: Optional[BM25Okapi] = None
_bm25_chunks: List[PolicyChunk] = []


def _tokenize(text: str) -> List[str]:
    """Tokenize text preserving currency, numbers, and rule codes."""
    # Normalize spaces and lowercase, but preserve $ and hyphens in codes like REF-001
    tokens = re.findall(r"[\$\w]+(?:-[\$\w]+)*", text.lower())
    return tokens


def get_bm25_index() -> tuple[BM25Okapi, List[PolicyChunk]]:
    """Return the initialized BM25 index and corresponding chunks."""
    global _bm25_index, _bm25_chunks
    chunks = get_indexed_chunks()

    if _bm25_index is not None and len(_bm25_chunks) == len(chunks):
        return _bm25_index, _bm25_chunks

    corpus = []
    for c in chunks:
        # Boost title and section by concatenating them with body content
        searchable_text = f"{c.title} {c.section} {c.subsection or ''} {c.content}"
        corpus.append(_tokenize(searchable_text))

    _bm25_index = BM25Okapi(corpus)
    _bm25_chunks = chunks
    log.info("rag.bm25.indexed", chunk_count=len(chunks))
    return _bm25_index, _bm25_chunks


def search_bm25(query: str, top_k: int = 15) -> List[Dict[str, Any]]:
    """
    Perform lexical BM25 search over all indexed policy chunks.
    Returns top-k candidate dictionaries with bm25_score.
    """
    try:
        bm25, chunks = get_bm25_index()
        tokenized_query = _tokenize(query)
        if not tokenized_query:
            return []

        doc_scores = bm25.get_scores(tokenized_query)

        # Sort indices by score descending
        ranked_indices = sorted(
            range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True
        )

        candidates = []
        for idx in ranked_indices[:top_k]:
            score = float(doc_scores[idx])
            if score > 0.01:  # Filter zero-match chunks
                payload = chunks[idx].to_dict()
                payload["bm25_score"] = round(score, 4)
                candidates.append(payload)

        return candidates
    except Exception as e:
        log.warning("rag.bm25.search_failed", error=str(e))
        return []
