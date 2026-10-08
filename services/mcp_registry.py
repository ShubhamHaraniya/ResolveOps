"""
services/mcp_registry.py
Unified Model Context Protocol (MCP) Registry.
Registers all 5 domain MCP servers (ticketing, crm, billing, access, kb).
Provides standardized discovery, schema inspection, annotation retrieval, and tool dispatch.
"""
from typing import Dict, Any, List, Optional, Tuple
import structlog

from services.mcp_ticketing import server as mcp_ticketing
from services.mcp_crm import server as mcp_crm
from services.mcp_billing import server as mcp_billing
from services.mcp_access import server as mcp_access
from services.mcp_kb import server as mcp_kb

log = structlog.get_logger()

# Mapping of namespace prefix to server module
MCP_SERVERS = {
    "ticketing": mcp_ticketing,
    "crm": mcp_crm,
    "billing": mcp_billing,
    "access": mcp_access,
    "iam": mcp_access,
    "kb": mcp_kb,
}


def _split_tool_name(tool_name: str) -> Tuple[str, str]:
    """Parse 'billing.issue_refund' -> ('billing', 'issue_refund')."""
    if "." in tool_name:
        parts = tool_name.split(".", 1)
        return parts[0], parts[1]
    # Fallback heuristic if unprefixed
    for prefix, server in MCP_SERVERS.items():
        for tool in server.list_tools():
            if tool["name"] == tool_name:
                return prefix, tool_name
    raise ValueError(f"Unknown or un-namespaced MCP tool: '{tool_name}'")


def list_all_tools() -> List[Dict[str, Any]]:
    """Return all tools across all 5 MCP servers with qualified names."""
    all_tools = []
    seen = set()
    for prefix, server in MCP_SERVERS.items():
        if prefix == "iam":  # alias for access
            continue
        for tool in server.list_tools():
            qualified_name = f"{prefix}.{tool['name']}"
            if qualified_name not in seen:
                seen.add(qualified_name)
                tool_copy = dict(tool)
                tool_copy["qualified_name"] = qualified_name
                all_tools.append(tool_copy)
    return all_tools


def get_tool_metadata(tool_name: str) -> Optional[Dict[str, Any]]:
    """Fetch tool definition and MCP annotations for a specific tool."""
    try:
        prefix, base_name = _split_tool_name(tool_name)
    except ValueError:
        return None

    server = MCP_SERVERS.get(prefix)
    if not server:
        return None

    for tool in server.list_tools():
        if tool["name"] == base_name:
            tool_copy = dict(tool)
            tool_copy["qualified_name"] = f"{prefix}.{base_name}"
            return tool_copy
    return None


async def dispatch_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Dispatch tool execution to the appropriate MCP server with annotations check.
    """
    prefix, base_name = _split_tool_name(tool_name)
    server = MCP_SERVERS.get(prefix)
    if not server:
        raise ValueError(f"No MCP server registered for prefix '{prefix}'")

    meta = get_tool_metadata(tool_name)
    annotations = (meta or {}).get("annotations", {})

    log.info(
        "mcp_registry.dispatch",
        tool=tool_name,
        prefix=prefix,
        base_name=base_name,
        read_only=annotations.get("readOnlyHint"),
        destructive=annotations.get("destructiveHint"),
        idempotent=annotations.get("idempotentHint"),
    )

    result = await server.call_tool(base_name, arguments, headers=headers)
    return result
