"""
backend/app/reliability/idempotency.py
Idempotency enforcement — prevents duplicate side effects.

Key: SHA256(ticket_id + ":" + tool + ":" + sorted_json(normalized_args))
Store: Redis (primary) + Postgres (durable fallback)
TTL: 7 days
"""
import hashlib
import json
import time
from typing import Any

import structlog

log = structlog.get_logger()

# In-memory store for development (Redis in production)
_store: dict[str, dict] = {}


def make_idempotency_key(ticket_id: str, tool: str, args: dict) -> str:
    """
    Deterministic idempotency key.
    SHA256(ticket_id + ":" + tool + ":" + sorted_json(normalized_args))
    """
    normalized = json.dumps(args, sort_keys=True, separators=(",", ":"))
    content = f"{ticket_id}:{tool}:{normalized}"
    return hashlib.sha256(content.encode()).hexdigest()


class IdempotencyStore:
    """
    Idempotency enforcement store.
    
    Usage:
        store = IdempotencyStore()
        key = store.make_key(ticket_id, tool, args)
        
        cached = store.get(key)
        if cached:
            return cached  # Return without re-executing
        
        result = await execute(...)
        store.set(key, result)
        return result
    """

    def __init__(self, redis_client=None, ttl_seconds: int = 7 * 24 * 3600):
        self._redis = redis_client
        self._ttl = ttl_seconds
        self._mem_store = _store

    def make_key(self, ticket_id: str, tool: str, args: dict) -> str:
        return make_idempotency_key(ticket_id, tool, args)

    def get(self, key: str) -> dict | None:
        """Return cached result if exists and not expired."""
        # Try Redis first
        if self._redis:
            try:
                data = self._redis.get(f"idem:{key}")
                if data:
                    return json.loads(data)
            except Exception as e:
                log.warning("idempotency.redis_get_failed", error=str(e))

        # Fallback to in-memory
        entry = self._mem_store.get(key)
        if entry:
            if entry.get("expires_at", 0) > time.time():
                log.info("idempotency.cache_hit", key=key[:16])
                return entry["result"]
            else:
                del self._mem_store[key]
        return None

    def set(self, key: str, result: Any, tool: str = "", ticket_id: str = "") -> None:
        """Cache execution result."""
        entry = {
            "result": result,
            "cached_at": time.time(),
            "expires_at": time.time() + self._ttl,
            "tool": tool,
            "ticket_id": ticket_id,
        }

        # Try Redis
        if self._redis:
            try:
                self._redis.setex(
                    f"idem:{key}",
                    self._ttl,
                    json.dumps({"result": result, "tool": tool, "ticket_id": ticket_id}),
                )
            except Exception as e:
                log.warning("idempotency.redis_set_failed", error=str(e))

        # Always store in memory too
        self._mem_store[key] = entry
        log.info("idempotency.cached", key=key[:16], tool=tool)

    def invalidate(self, key: str) -> None:
        """Invalidate a cached result (e.g., when approval is edited)."""
        self._mem_store.pop(key, None)
        if self._redis:
            try:
                self._redis.delete(f"idem:{key}")
            except Exception:
                pass


# Singleton
_idem_store: IdempotencyStore | None = None


def get_idempotency_store() -> IdempotencyStore:
    global _idem_store
    if _idem_store is None:
        _idem_store = IdempotencyStore()
    return _idem_store
