"""
Audit store tests: PII redaction, hash chaining, tamper / deletion / fork detection.
"""
import pytest_asyncio
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import create_async_engine

from app.audit.store import GENESIS_HASH, append_audit_event, redact_pii, verify_chain
from app.db import session as db_session
from app.db.models import AuditEvent, AuditLog, Base


def test_pii_redaction_email():
    redacted = redact_pii("john.smith@acme-corp.com")
    assert redacted == "j***@acme-corp.com"
    assert "john.smith" not in redacted


def test_pii_redaction_dict_keeps_non_pii():
    redacted = redact_pii({"email": "user@example.com", "amount_cents": 3000, "invoice_id": "INV-001"})
    assert redacted["email"] == "u***@example.com"
    assert redacted["amount_cents"] == 3000
    assert redacted["invoice_id"] == "INV-001"


@pytest_asyncio.fixture
async def audit_db(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'audit.db').as_posix()}")
    previous = db_session.AsyncSessionLocal.kw.get("bind")
    db_session.AsyncSessionLocal.configure(bind=engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    db_session.AsyncSessionLocal.configure(bind=previous)
    await engine.dispose()


async def append_n(n, ticket="TKT-1"):
    return [
        await append_audit_event(event=AuditEvent.proposed, ticket_id=ticket, run_id=f"RUN-{i}", result_status=str(i))
        for i in range(n)
    ]


async def verify():
    async with db_session.AsyncSessionLocal() as db:
        return await verify_chain(db)


async def test_empty_chain_is_valid(audit_db):
    result = await verify()
    assert result["valid"] is True and result["total_events"] == 0


async def test_chain_links_each_row_to_the_previous(audit_db):
    events = await append_n(4)
    assert events[0]["prev_hash"] == GENESIS_HASH
    for prev, cur in zip(events, events[1:]):
        assert cur["prev_hash"] == prev["row_hash"]
    result = await verify()
    assert result["valid"] is True and result["verified_events"] == 4
    assert result["head_hash"] == events[-1]["row_hash"]


async def test_args_are_redacted_but_hashed(audit_db):
    ev = await append_audit_event(
        event=AuditEvent.tool_call_start, ticket_id="T", args={"email": "jane@acme.com", "amount_cents": 100},
    )
    assert ev["args_redacted"]["email"] == "j***@acme.com"


async def test_edited_row_is_detected(audit_db):
    events = await append_n(3)
    async with db_session.AsyncSessionLocal() as db:
        await db.execute(update(AuditLog).where(AuditLog.id == events[1]["id"]).values(result_status="TAMPERED"))
        await db.commit()
    result = await verify()
    assert result["valid"] is False
    assert events[1]["id"] in result["error"]


async def test_deleted_row_is_detected(audit_db):
    events = await append_n(4)
    async with db_session.AsyncSessionLocal() as db:
        await db.execute(delete(AuditLog).where(AuditLog.id == events[1]["id"]))
        await db.commit()
    result = await verify()
    assert result["valid"] is False
    assert "not reachable" in result["error"]


async def test_forked_chain_is_detected(audit_db):
    events = await append_n(2)
    async with db_session.AsyncSessionLocal() as db:
        db.add(AuditLog(
            id="forged", run_id="r", ticket_id="TKT-1", actor_type="agent", actor_id="x",
            event=AuditEvent.proposed, prev_hash=events[0]["prev_hash"], row_hash="f" * 64,
        ))
        await db.commit()
    result = await verify()
    assert result["valid"] is False
    assert "forks" in result["error"]
