"""
tests/reliability/test_mcp_servers.py
Unit tests for the 5 standardized FastMCP Protocol Servers and MCP Registry.
Validates schemas, annotations (readOnlyHint, destructiveHint, idempotentHint), and role safety.
"""
import asyncio
import pytest
from services import mcp_registry
from services.mcp_ticketing import server as mcp_ticketing
from services.mcp_crm import server as mcp_crm
from services.mcp_billing import server as mcp_billing
from services.mcp_access import server as mcp_access


def test_all_servers_registered():
    """Verify all 5 core domains are registered in MCP registry."""
    tools = mcp_registry.list_all_tools()
    assert len(tools) >= 15

    names = {t["qualified_name"] for t in tools}
    assert "ticketing.get_ticket" in names
    assert "crm.find_contact" in names
    assert "billing.issue_refund" in names
    assert "access.grant_access" in names
    assert "kb.search_policy" in names


def test_mcp_annotations_present():
    """Verify that every registered tool has explicit MCP annotations."""
    tools = mcp_registry.list_all_tools()
    for tool in tools:
        assert "annotations" in tool, f"Tool {tool['name']} missing annotations"
        annotations = tool["annotations"]
        assert "readOnlyHint" in annotations
        assert "destructiveHint" in annotations
        assert "idempotentHint" in annotations


def test_read_only_tools_annotations():
    """Verify read-only tools are marked correctly."""
    read_tools = [
        "ticketing.get_ticket",
        "crm.get_account",
        "crm.find_contact",
        "billing.get_invoice",
        "billing.get_subscription",
        "access.get_user",
        "kb.search_policy",
    ]
    for tool_name in read_tools:
        meta = mcp_registry.get_tool_metadata(tool_name)
        assert meta is not None, f"Metadata missing for {tool_name}"
        assert meta["annotations"]["readOnlyHint"] is True
        assert meta["annotations"]["destructiveHint"] is False


def test_destructive_write_tools_annotations():
    """Verify destructive tools are marked correctly."""
    destructive_tools = [
        "billing.issue_refund",
        "access.grant_access",
        "access.reset_mfa",
    ]
    for tool_name in destructive_tools:
        meta = mcp_registry.get_tool_metadata(tool_name)
        assert meta is not None
        assert meta["annotations"]["readOnlyHint"] is False
        assert meta["annotations"]["destructiveHint"] is True


def test_mcp_ticketing_execution():
    """Test get_ticket execution."""
    res = asyncio.run(mcp_ticketing.call_tool("get_ticket", {"ticket_id": "TKT-001"}))
    assert res.get("id") == "TKT-001"
    assert res.get("account_id") == "ACC-001"


def test_mcp_crm_execution():
    """Test find_contact execution."""
    res = asyncio.run(mcp_crm.call_tool("find_contact", {"email": "john.smith@acme-corp.com"}))
    assert res.get("email") == "john.smith@acme-corp.com"
    assert res.get("id") == "CON-001"


def test_mcp_billing_execution_and_idempotency():
    """Test issue_refund execution and idempotency enforcement."""
    key = "test-idemp-refund-key-001"
    args = {
        "invoice_id": "INV-001",
        "amount_cents": 2500,
        "reason": "duplicate_charge",
        "idempotency_key": key,
    }
    # First execution
    res1 = asyncio.run(mcp_billing.call_tool("issue_refund", args))
    assert res1.get("status") == "succeeded"

    # Second execution with same key -> idempotent cached result
    res2 = asyncio.run(mcp_billing.call_tool("issue_refund", args))
    assert res2.get("idempotent_replay") is True
    assert res2.get("id") == res1.get("id")


@pytest.mark.parametrize("amount", [-50000, 0, 999999999])
def test_mcp_billing_rejects_out_of_bounds_refund_amounts(amount):
    args = {"invoice_id": "INV-001", "amount_cents": amount, "reason": "test", "idempotency_key": f"bounds-{amount}"}
    res = asyncio.run(mcp_billing.call_tool("issue_refund", args))
    assert res.get("status") == "failed" or "error" in res


def test_mcp_access_security_block_admin():
    """Test that grant_access strictly forbids 'admin' role."""
    with pytest.raises(ValueError, match="FORBIDDEN"):
        asyncio.run(mcp_access.call_tool("grant_access", {
            "account_id": "ACCT-001",
            "user_email": "attacker@corp.com",
            "role": "admin",
            "reason": "escalation",
        }))

    with pytest.raises(ValueError, match="FORBIDDEN"):
        asyncio.run(mcp_access.call_tool("grant_access", {
            "account_id": "ACCT-001",
            "user_email": "attacker@corp.com",
            "role": "prod-admin",
            "reason": "escalation",
        }))


def test_mcp_access_allows_viewer():
    """Test that grant_access permits 'viewer' role."""
    res = asyncio.run(mcp_access.call_tool("grant_access", {
        "account_id": "ACCT-001",
        "user_email": "auditor@corp.com",
        "role": "viewer",
        "reason": "routine audit",
    }))
    assert res.get("status") == "active"
    assert res.get("role") == "viewer"
