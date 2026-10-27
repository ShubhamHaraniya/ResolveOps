"""
backend/app/observability/langfuse_client.py
Production Langfuse telemetry integration for ResolveOps.
Tracks LangGraph agent traces, LLM generations (Groq), RAG context retrieval,
tool executions, policy decisions, and latency metrics.
Includes graceful local telemetry fallback if remote Langfuse is offline.
"""
import os
import uuid
from typing import Dict, Any, Optional, List
import structlog

from app.config import settings

log = structlog.get_logger()

_langfuse_instance = None
_is_initialized = False


class ResolveOpsTelemetry:
    """
    Unified Observability Client for ResolveOps.
    Wraps Langfuse SDK and provides safe trace lifecycle helpers.
    Supports both Langfuse v4 (OpenTelemetry / TraceContext) and v2/v3 SDKs,
    with zero-penalty local fallback if keys are missing or host is offline.
    """

    def __init__(self):
        self.host = getattr(settings, "langfuse_host", "http://localhost:3000")
        self.public_key = getattr(settings, "langfuse_public_key", "").strip()
        self.secret_key = getattr(settings, "langfuse_secret_key", "").strip()
        self.enabled = bool(self.public_key and self.secret_key)
        self.client = None

        if self.enabled:
            # Propagate to environment for LangChain/LangGraph and OpenTelemetry integrations
            os.environ["LANGFUSE_PUBLIC_KEY"] = self.public_key
            os.environ["LANGFUSE_SECRET_KEY"] = self.secret_key
            os.environ["LANGFUSE_HOST"] = self.host
            try:
                from langfuse import Langfuse
                self.client = Langfuse(
                    public_key=self.public_key,
                    secret_key=self.secret_key,
                    host=self.host,
                )
                log.info("telemetry.langfuse.connected", host=self.host)
            except Exception as e:
                log.warning("telemetry.langfuse.init_failed_using_fallback", error=str(e))
                self.client = None
                self.enabled = False
        else:
            log.info("telemetry.langfuse.local_mode", note="Keys not configured; using local structured telemetry")

    def _get_trace_context(self, trace_id: str):
        """Construct TraceContext for Langfuse v4 if available."""
        try:
            from langfuse.types import TraceContext
            return TraceContext(trace_id=trace_id)
        except Exception:
            return None

    def create_trace(
        self,
        name: str,
        ticket_id: str,
        run_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create or initialize trace for ticket run. Returns trace_id."""
        trace_id = run_id.replace("-", "")[:32] if run_id else uuid.uuid4().hex
        meta = metadata or {}
        meta["ticket_id"] = ticket_id
        meta["run_id"] = run_id

        log.info(
            "telemetry.trace.start",
            trace_id=trace_id,
            name=name,
            ticket_id=ticket_id,
            tags=tags or [],
        )

        if self.enabled and self.client:
            try:
                if hasattr(self.client, "trace"):
                    # Langfuse v2/v3
                    self.client.trace(
                        id=trace_id,
                        name=name,
                        metadata=meta,
                        tags=tags or [],
                    )
                elif hasattr(self.client, "create_event"):
                    # Langfuse v4
                    ctx = self._get_trace_context(trace_id)
                    if ctx:
                        self.client.create_event(
                            name=name,
                            trace_context=ctx,
                            metadata=meta,
                        )
            except Exception as e:
                log.warning("telemetry.langfuse.trace_failed", error=str(e))

        return trace_id

    def record_generation(
        self,
        trace_id: str,
        name: str,
        model: str,
        prompt: Any,
        completion: Any,
        latency_ms: float,
        usage: Optional[Dict[str, Any]] = None,
        cost_usd: Optional[float] = None,
    ) -> None:
        """Record an LLM completion generation event."""
        log.info(
            "telemetry.generation",
            trace_id=trace_id,
            name=name,
            model=model,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            usage=usage or {},
        )

        if self.enabled and self.client:
            try:
                if hasattr(self.client, "generation"):
                    self.client.generation(
                        trace_id=trace_id,
                        name=f"llm_{name}",
                        model=model,
                        prompt=prompt,
                        completion=completion,
                        usage=usage,
                        metadata={"latency_ms": latency_ms, "cost_usd": cost_usd},
                    )
                elif hasattr(self.client, "start_observation"):
                    ctx = self._get_trace_context(trace_id)
                    if ctx:
                        obs = self.client.start_observation(
                            name=f"llm_{name}",
                            as_type="generation",
                            trace_context=ctx,
                            model=model,
                            input=prompt,
                            output=completion,
                            metadata={
                                "latency_ms": latency_ms,
                                "cost_usd": cost_usd,
                                "usage": usage or {},
                            },
                        )
                        obs.end()
                elif hasattr(self.client, "create_event"):
                    ctx = self._get_trace_context(trace_id)
                    self.client.create_event(
                        name=f"llm_{name}",
                        trace_context=ctx,
                        metadata={
                            "model": model,
                            "latency_ms": latency_ms,
                            "cost_usd": cost_usd,
                            "usage": usage or {},
                        },
                    )
            except Exception as e:
                log.warning("telemetry.langfuse.generation_failed", error=str(e))

    def record_span(
        self,
        trace_id: str,
        name: str,
        input_data: Any = None,
        output_data: Any = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Record an operational span (RAG retrieval, tool execution, policy check)."""
        log.info(
            "telemetry.span",
            trace_id=trace_id,
            span_name=name,
            duration_ms=duration_ms,
        )

        if self.enabled and self.client:
            try:
                if hasattr(self.client, "span"):
                    self.client.span(
                        trace_id=trace_id,
                        name=name,
                        input=input_data,
                        output=output_data,
                        metadata={"duration_ms": duration_ms},
                    )
                elif hasattr(self.client, "create_event"):
                    ctx = self._get_trace_context(trace_id)
                    self.client.create_event(
                        name=name,
                        trace_context=ctx,
                        metadata={
                            "duration_ms": duration_ms,
                            "input_preview": str(input_data)[:200] if input_data else None,
                            "output_preview": str(output_data)[:200] if output_data else None,
                        },
                    )
            except Exception as e:
                log.warning("telemetry.langfuse.span_failed", error=str(e))

    def get_langchain_callback(self, trace_id: Optional[str] = None):
        """
        Return Langfuse callback handler for LangGraph / LangChain workflows.
        Returns None when Langfuse is not enabled to avoid network delays.
        """
        if not self.enabled:
            return None

        try:
            from langfuse.langchain import CallbackHandler
            if trace_id:
                ctx = self._get_trace_context(trace_id)
                if ctx:
                    return CallbackHandler(trace_context=ctx)
            return CallbackHandler()
        except Exception:
            try:
                from langfuse.callback import CallbackHandler
                return CallbackHandler()
            except Exception as e:
                log.warning("telemetry.langfuse.callback_init_failed", error=str(e))
                return None

    def flush(self) -> None:
        """Flush pending events to remote server."""
        if self.enabled and self.client and hasattr(self.client, "flush"):
            try:
                self.client.flush()
            except Exception:
                pass


_telemetry_client: Optional[ResolveOpsTelemetry] = None


def get_telemetry() -> ResolveOpsTelemetry:
    """Return singleton telemetry instance."""
    global _telemetry_client
    if _telemetry_client is None:
        _telemetry_client = ResolveOpsTelemetry()
    return _telemetry_client
