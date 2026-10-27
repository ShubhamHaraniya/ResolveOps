"""
End-to-end fixtures: real FastAPI app + real LangGraph workflow + real policy engine and
gateway, backed by a temporary SQLite database. Only the Groq LLM is replaced by a scripted
fake, so no network or API key is needed. (The mock HTTP services are not started: the
workflow falls back to the in-process MCP servers when they are unreachable.)
"""
import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import session as db_session
from app.db.models import Base
from app.llm.schemas import (
    Classification, LLMCallResult, ProposedAction, ProposedResolution, TokenUsage,
)


class FakeGroq:
    """Scripted stand-in for the Groq client. `actions` is what the 'model' proposes."""

    def __init__(self):
        self.actions: list[ProposedAction] = []
        self.category = "refund_request"
        self.draft_reply = "Thanks for reaching out - we are looking into this."

    async def complete_structured(self, model, messages, response_model, temperature=0.1, call_label="llm_call"):
        if response_model is Classification:
            result = Classification(
                category=self.category, urgency="medium", sentiment="neutral", confidence=0.9,
                brief_reason="scripted",
            )
        else:
            result = ProposedResolution(
                actions=list(self.actions), draft_reply=self.draft_reply, reasoning_summary="scripted",
            )
        return LLMCallResult(
            result=result, usage=TokenUsage(model=model, estimated_cost_usd=0.001),
            latency_ms=1.0, model=model, call_id="fake",
        )


def refund_action(amount_cents=3000, invoice_id="INV-001", key=None):
    args = {"invoice_id": invoice_id, "amount_cents": amount_cents, "reason": "Duplicate charge"}
    if key:
        args["idempotency_key"] = key
    return ProposedAction(tool="billing.issue_refund", arguments=args, reason="duplicate charge", risk_level="medium")


@pytest.fixture
def fake_groq(monkeypatch):
    fake = FakeGroq()
    monkeypatch.setattr("app.graph.nodes.classify.get_groq_client", lambda: fake)
    monkeypatch.setattr("app.graph.nodes.plan_action.get_groq_client", lambda: fake)
    return fake


@pytest_asyncio.fixture
async def app_client(tmp_path, monkeypatch, fake_groq):
    """HTTP client bound to the real app with a fresh DB and clean in-memory state."""
    from app.audit.gateway_sink import flush_pending, persist_gateway_event
    from app.db.seed import seed_initial_data
    from app.graph import runner
    from app.main import create_app
    from services.gateway import gateway
    from services.mcp_billing import server as mcp_billing

    monkeypatch.setenv("BILLING_ERROR_RATE", "0")

    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}")
    previous_bind = db_session.AsyncSessionLocal.kw.get("bind")
    db_session.AsyncSessionLocal.configure(bind=engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_initial_data(include_demo_history=False)

    runner._ACTIVE_RUNS.clear()
    gateway._approvals.clear()
    gateway._idempotency_store.clear()
    gateway._run_budgets.clear()
    gateway._audit_log.clear()
    gateway._kill_switch = False
    mcp_billing._refunds.clear()
    mcp_billing._idempotency_store.clear()
    gateway.set_audit_sink(persist_gateway_event)

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    await flush_pending()
    gateway.set_audit_sink(None)
    gateway._kill_switch = False
    db_session.AsyncSessionLocal.configure(bind=previous_bind)
    await engine.dispose()


@pytest_asyncio.fixture
async def client_and_llm(app_client, fake_groq):
    return app_client, fake_groq
