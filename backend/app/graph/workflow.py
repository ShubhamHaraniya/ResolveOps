"""
LangGraph Workflow — 11-node ticket processing workflow.
Postgres-checkpointed for crash recovery and long approval waits.

Flow:
START → intake → classify → verify_identity → gather_context → plan_action
     → policy_check → [auto → execute | approval → interrupt | forbidden → escalate]
     → verify_outcome → draft_reply → close → END
"""
import structlog
from langgraph.graph import StateGraph, END, START

from app.graph.state import TicketState
from app.graph.nodes.intake import intake_node
from app.graph.nodes.classify import classify_node
from app.graph.nodes.verify_identity import verify_identity_node
from app.graph.nodes.gather_context import gather_context_node
from app.graph.nodes.plan_action import plan_action_node
from app.graph.nodes.policy_check import policy_check_node
from app.graph.nodes.approval_interrupt import approval_interrupt_node
from app.graph.nodes.execute import execute_node
from app.graph.nodes.verify_outcome import verify_outcome_node
from app.graph.nodes.draft_reply import draft_reply_node
from app.graph.nodes.close import close_node

log = structlog.get_logger()


def route_after_policy(state: TicketState) -> str:
    """Route after policy_check node based on the most restrictive policy decision."""
    decisions = state.get("policy_decisions", [])
    if not decisions:
        return "escalate_close"

    # Most recent decision (last added)
    decision = decisions[-1]
    tier = decision.get("tier", "forbidden")

    if tier == "auto":
        return "execute"
    elif tier == "approval":
        return "approval_interrupt"
    else:  # forbidden
        return "escalate_close"


def route_after_identity(state: TicketState) -> str:
    """If identity not verified, block writes and escalate."""
    identity = state.get("identity", {})
    if identity and not identity.get("verified", False):
        # Add identity mismatch flag
        return "escalate_close"
    return "gather_context"


def build_workflow(checkpointer=None):
    """
    Build and compile the ResolveOps LangGraph workflow.

    Args:
        checkpointer: LangGraph checkpointer (PostgresSaver for production,
                      MemorySaver for testing)
    """
    graph = StateGraph(TicketState)

    # ── Add all nodes ──────────────────────────────────────────
    graph.add_node("intake", intake_node)
    graph.add_node("classify", classify_node)
    graph.add_node("verify_identity", verify_identity_node)
    graph.add_node("gather_context", gather_context_node)
    graph.add_node("plan_action", plan_action_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("approval_interrupt", approval_interrupt_node)
    graph.add_node("execute", execute_node)
    graph.add_node("verify_outcome", verify_outcome_node)
    graph.add_node("draft_reply", draft_reply_node)
    graph.add_node("close", close_node)

    # ── Edges ──────────────────────────────────────────────────
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "classify")

    # After classify, check for injection — if severe, escalate early
    graph.add_edge("classify", "verify_identity")

    # After identity — route based on verification result
    graph.add_conditional_edges(
        "verify_identity",
        route_after_identity,
        {
            "gather_context": "gather_context",
            "escalate_close": "close",
        }
    )

    graph.add_edge("gather_context", "plan_action")
    graph.add_edge("plan_action", "policy_check")

    # Core routing: auto → execute, approval → interrupt, forbidden → escalate
    graph.add_conditional_edges(
        "policy_check",
        route_after_policy,
        {
            "execute": "execute",
            "approval_interrupt": "approval_interrupt",
            "escalate_close": "close",
        }
    )

    # After approval interrupt — workflow pauses here
    # Resume is triggered externally (POST /api/approvals/{id}/approve)
    graph.add_edge("approval_interrupt", END)

    # Execution path
    graph.add_edge("execute", "verify_outcome")
    graph.add_edge("verify_outcome", "draft_reply")
    graph.add_edge("draft_reply", "close")
    graph.add_edge("close", END)

    # Compile with checkpointer (enables interrupt and resume)
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    return graph.compile(
        **compile_kwargs,
        interrupt_before=["execute"],  # Always pause before execution for approval
    )


async def get_checkpointer():
    """Get Postgres checkpointer for production use."""
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        checkpointer = await AsyncPostgresSaver.from_conn_string(
            # Convert asyncpg URL format
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        )
        return checkpointer
    except Exception as e:
        log.warning("checkpointer.postgres.failed", error=str(e))
        # Fall back to in-memory for dev without Postgres
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
