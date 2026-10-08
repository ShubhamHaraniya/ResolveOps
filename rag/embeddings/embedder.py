"""
Local FastEmbed Embedding Engine for ResolveOps.
Uses CPU-optimized ONNX runtime with BAAI/bge-small-en-v1.5 (384-dim).
Operates 100% locally with zero cloud API leakage.
Includes deterministic fallback for isolated/offline test environments.
"""
import hashlib
import math
from typing import List, Optional
import structlog

log = structlog.get_logger()

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_DIM = 384


class FastEmbedEmbedder:
    """Wrapper around FastEmbed TextEmbedding model."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.dim = DEFAULT_DIM
        self._model = None
        self._use_fallback = False

    def _init_model(self):
        if self._model is not None or self._use_fallback:
            return

        try:
            from fastembed import TextEmbedding
            log.info("rag.embedder.init", model=self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
            log.info("rag.embedder.ready", model=self.model_name)
        except Exception as e:
            log.warning("rag.embedder.fallback", error=str(e))
            self._use_fallback = True

    def _fallback_embed(self, text: str) -> List[float]:
        """Deterministic pseudo-embedding for offline/test environments."""
        vec = [0.0] * self.dim
        tokens = text.lower().split()
        for i, token in enumerate(tokens):
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            vec[idx] += 1.0 / (1.0 + math.log(i + 1))
        # Normalize vector
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate dense embeddings for a batch of texts."""
        self._init_model()
        if self._use_fallback or self._model is None:
            return [self._fallback_embed(t) for t in texts]

        try:
            embeddings_iter = self._model.embed(texts)
            return [list(vec) for vec in embeddings_iter]
        except Exception as e:
            log.warning("rag.embedder.embed_failed", error=str(e))
            return [self._fallback_embed(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        """Generate dense embedding for a search query string."""
        results = self.embed_texts([query])
        return results[0] if results else [0.0] * self.dim


# Global singleton instance
_embedder_instance: Optional[FastEmbedEmbedder] = None


def get_embedder(model_name: str = DEFAULT_MODEL) -> FastEmbedEmbedder:
    """Return the shared FastEmbedEmbedder instance."""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = FastEmbedEmbedder(model_name=model_name)
    return _embedder_instance
