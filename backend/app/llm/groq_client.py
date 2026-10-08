"""
Groq API Client
Async client using Groq's OpenAI-compatible endpoint.
Handles: retries, timeouts, structured outputs, token tracking, tracing.
"""
import asyncio
import json
import time
import uuid
from typing import Any, TypeVar, Type

import httpx
import structlog
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.config import settings
from app.llm.schemas import TokenUsage, LLMCallResult

log = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Approximate token prices for cost estimation (update in config/model_prices.yaml)
MODEL_PRICES_USD_PER_1M = {
    "openai/gpt-oss-120b": {"input": 0.90, "output": 0.90},
    "openai/gpt-oss-20b": {"input": 0.20, "output": 0.20},
    # Fallback
    "default": {"input": 1.0, "output": 1.0},
}


class GroqRetryableError(Exception):
    """429, 503 — transient, safe to retry."""


class GroqStructuredOutputError(Exception):
    """Response didn't parse into the expected schema."""


class GroqClient:
    """
    Async Groq API client using OpenAI-compatible endpoint.
    Base URL: https://api.groq.com/openai/v1

    IMPORTANT: GROQ_API_KEY is NEVER sent to the frontend.
    """

    def __init__(self):
        self._api_key = settings.groq_api_key
        self._base_url = GROQ_BASE_URL
        self._timeout = settings.groq_timeout_seconds
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )

    async def close(self):
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(GroqRetryableError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete_structured(
        self,
        model: str,
        messages: list[dict],
        response_model: Type[T],
        temperature: float = 0.1,
        call_label: str = "llm_call",
    ) -> LLMCallResult:
        """
        Call Groq with structured JSON output.
        Returns LLMCallResult with parsed response and token usage.

        Uses response_format=json_object for structured outputs.
        Validates response against response_model schema.
        """
        call_id = str(uuid.uuid4())[:8]
        t0 = time.monotonic()

        log.info(
            "groq.call.start",
            model=model,
            call_label=call_label,
            call_id=call_id,
            message_count=len(messages),
        )

        schema = response_model.model_json_schema()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": settings.groq_max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": schema,
                    "strict": True,
                },
            },
        }

        try:
            resp = await self._client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as e:
            raise GroqRetryableError(f"Groq request timed out: {e}") from e
        except httpx.ConnectError as e:
            raise GroqRetryableError(f"Groq connection error: {e}") from e

        if resp.status_code in (429, 503):
            raise GroqRetryableError(f"Groq {resp.status_code}: {resp.text[:200]}")

        if resp.status_code != 200:
            log.error("groq.call.error", status=resp.status_code, body=resp.text[:500])
            raise Exception(f"Groq API error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        latency_ms = round((time.monotonic() - t0) * 1000, 1)

        # Parse usage
        usage_data = data.get("usage", {})
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        prices = MODEL_PRICES_USD_PER_1M.get(model, MODEL_PRICES_USD_PER_1M["default"])
        cost = (prompt_tokens * prices["input"] + completion_tokens * prices["output"]) / 1_000_000

        usage = TokenUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=round(cost, 6),
        )

        # Parse content
        content = data["choices"][0]["message"]["content"]
        try:
            parsed_dict = json.loads(content)
            parsed = response_model.model_validate(parsed_dict)
        except Exception as e:
            log.error("groq.parse.error", error=str(e), content=content[:500])
            raise GroqStructuredOutputError(
                f"Failed to parse {response_model.__name__}: {e}"
            ) from e

        log.info(
            "groq.call.done",
            model=model,
            call_label=call_label,
            call_id=call_id,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
        )

        return LLMCallResult(
            result=parsed,
            usage=usage,
            latency_ms=latency_ms,
            model=model,
            call_id=call_id,
        )

    async def complete_text(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> tuple[str, TokenUsage]:
        """Free-text completion — for draft replies only (not for decisions)."""
        t0 = time.monotonic()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000,
        }
        resp = await self._client.post("/chat/completions", json=payload)
        if resp.status_code != 200:
            raise Exception(f"Groq text API error: {resp.status_code}")

        data = resp.json()
        usage_data = data.get("usage", {})
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        prices = MODEL_PRICES_USD_PER_1M.get(model, MODEL_PRICES_USD_PER_1M["default"])
        cost = (prompt_tokens * prices["input"] + completion_tokens * prices["output"]) / 1_000_000

        usage = TokenUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=round(cost, 6),
        )
        content = data["choices"][0]["message"]["content"]
        return content, usage


# Singleton
_groq_client: GroqClient | None = None


def get_groq_client() -> GroqClient:
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
