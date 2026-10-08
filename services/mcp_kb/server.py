"""
MCP Knowledge Base Server (mcp_kb).
Provides standardized MCP tools for searching Northwind Cloud policy documentation.
Annotated with readOnlyHint=True and idempotentHint=True.
"""
from typing import Dict, Any, Optional
import structlog
from rag.service import search_policies

log = structlog.get_logger()

# Tool definition conforming to Model Context Protocol (MCP) tool schema
SEARCH_POLICY_TOOL = {
    "name": "search_policy",
    "description": (
        "Search Northwind Cloud policy documents for refund limits, billing terms, "
        "access delegation rules, MFA requirements, SLA credits, and operational policies."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query or specific rule identifier (e.g., '$50 refund', 'REF-001')",
            },
            "category": {
                "type": "string",
                "description": "Optional operational category such as 'refund', 'billing', 'access', 'plan'",
            },
            "top_k": {
                "type": "integer",
                "default": 4,
                "description": "Number of high-relevance chunks to return (default 4)",
            },
        },
        "required": ["query"],
    },
    "annotations": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    },
}


def list_tools() -> list[dict]:
    """Return all tools registered with this MCP server."""
    return [SEARCH_POLICY_TOOL]


async def call_tool(name: str, arguments: dict) -> Dict[str, Any]:
    """Execute an MCP tool call."""
    if name != "search_policy":
        raise ValueError(f"Unknown MCP tool '{name}' on mcp_kb server")

    query = arguments.get("query", "")
    category = arguments.get("category")
    top_k = int(arguments.get("top_k", 4))

    log.info("mcp_kb.search_policy", query=query, category=category)
    result = search_policies(query=query, category=category, top_k=top_k)
    return result
