"""
services/gateway/tokens.py
Scoped JWT generation and validation for gateway authentication.

Each JWT is scoped to a specific (run_id, ticket_id, tool, exp).
Tampering with any field → signature verification fails.
"""
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, UTC, timedelta
from typing import Any

# Import from config (lazy to avoid circular)
def _get_secret() -> str:
    import os
    secret = os.environ.get("GATEWAY_JWT_SECRET")
    if not secret:
        raise ValueError("GATEWAY_JWT_SECRET env var is required")
    return secret


class ScopedJWT:
    """
    Simple HMAC-SHA256 scoped token (no external JWT library needed).
    
    Payload: {run_id, ticket_id, tool, args_hash, iat, exp}
    Signature: HMAC-SHA256(header.payload, secret)
    
    Properties:
    - Bound to exactly one tool call with specific args
    - Expires in 1 hour by default (approval tokens: 24h)
    - Not replayable after expiry
    """

    ALGORITHM = "HS256"

    def __init__(self, secret: str = None):
        self._secret = secret or _get_secret()

    def _b64(self, data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    def _unb64(self, data: str) -> bytes:
        import base64
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def generate(
        self,
        run_id: str,
        ticket_id: str,
        tool: str,
        args_hash: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Generate a scoped token for a specific tool call."""
        now = int(time.time())
        header = {"alg": self.ALGORITHM, "typ": "RJWT"}
        payload = {
            "run_id": run_id,
            "ticket_id": ticket_id,
            "tool": tool,
            "args_hash": args_hash,
            "iat": now,
            "exp": now + expires_in_seconds,
            "jti": str(uuid.uuid4()),
        }
        h = self._b64(json.dumps(header, separators=(",", ":")).encode())
        p = self._b64(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{h}.{p}".encode()
        sig = hmac.new(self._secret.encode(), signing_input, hashlib.sha256).digest()
        return f"{h}.{p}.{self._b64(sig)}"

    def validate(
        self,
        token: str,
        expected_run_id: str,
        expected_ticket_id: str,
        expected_tool: str,
        expected_args_hash: str,
    ) -> dict:
        """
        Validate token and return payload.
        Raises ValueError with specific reason on any validation failure.
        """
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        h, p, sig_b64 = parts
        signing_input = f"{h}.{p}".encode()
        expected_sig = hmac.new(self._secret.encode(), signing_input, hashlib.sha256).digest()
        actual_sig = self._unb64(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Token signature verification failed")

        payload = json.loads(self._unb64(p))

        now = int(time.time())
        if payload.get("exp", 0) < now:
            raise ValueError(f"Token expired at {payload.get('exp')}")

        if payload.get("run_id") != expected_run_id:
            raise ValueError("Token run_id mismatch")
        if payload.get("ticket_id") != expected_ticket_id:
            raise ValueError("Token ticket_id mismatch")
        if payload.get("tool") != expected_tool:
            raise ValueError("Token tool mismatch")
        if payload.get("args_hash") != expected_args_hash:
            raise ValueError("Token args_hash mismatch — possible argument tampering")

        return payload


def make_args_hash(tool: str, args: dict) -> str:
    """
    Deterministic hash of tool + args for token binding and approval matching.
    SHA256(tool + ":" + sorted_json(normalized_args))
    """
    normalized = json.dumps(args, sort_keys=True, separators=(",", ":"))
    content = f"{tool}:{normalized}"
    return hashlib.sha256(content.encode()).hexdigest()


# Singleton
_jwt_instance: ScopedJWT | None = None


def get_jwt() -> ScopedJWT:
    global _jwt_instance
    if _jwt_instance is None:
        _jwt_instance = ScopedJWT()
    return _jwt_instance
