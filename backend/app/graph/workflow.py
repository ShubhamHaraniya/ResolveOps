"""
LangGraph Workflow — 11-node ticket processing workflow.
Postgres-checkpointed for crash recovery and long approval waits.

Flow:
START → intake → classify → verify_identity → gather_context → plan_action
     → policy_check → [auto → execute | approval → interrupt | forbidden → escalate]
     → verify_outcome → draft_reply → close → END
"""
import time
import structlog
from langgraph.graph import StateGraph, END, START

from app.observability.langfuse_client import get_telemetry
from app.graph.state import TicketState
from app.graph.nodes.intake import intake_node
from app.graph.nodes.classify import classify_node
from app.graph.nodes.verify_identity import verify_identity_node
from app.graph.nodes.gather_context import gather_context_node
from app.graph.nodes.plan_action import plan_action_node
from app.graph.nodes.policy_check import policy_check_node
from app.graph.nodes.approval_interrupt import approval_interrupt_node
from app.graph.nodes.execute import execute_node
from app.graph.nodes.verify_outcome import verify_outcome_node, draft_reply_node, close_node

log = structlog.get_logger()


def instrument_node(node_key: str, node_fn):
    """Wrap node function with timing, telemetry, and error tracking."""
    async def _wrapped(state: TicketState) -> dict:
        t0 = time.perf_counter()
        trace_id = state.get("langfuse_trace_id") or state.get("run_id")
        telemetry = get_telemetry()
        try:
            output = await node_fn(state)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            if not isinstance(output, dict):
                output = {}
            output["_node_duration_ms"] = duration_ms
            output["_last_node"] = node_key
            if trace_id:
                telemetry.record_span(
                    trace_id=trace_id,
                    name=f"langgraph_{node_key}",
                    duration_ms=duration_ms,
                )
            return output
        except Exception as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            if trace_id:
                telemetry.record_span(
                    trace_id=trace_id,
                    name=f"langgraph_{node_key}_failed",
                    duration_ms=duration_ms,
                    output_data={"error": str(e)},
                )
            raise
    return _wrapped


def route_at_start(state: TicketState) -> str:
    """Route from START: initial run vs resumed approval."""
    res_val = state.get("resume_approval")
    action_type = state.get("action_type")
    resumed = bool(res_val or action_type)
    log.info("workflow.route_at_start", res_val=res_val, resumed=resumed, action_type=action_type, ticket_id=state.get("ticket_id"))
    if resumed:
        if action_type in ("reject", "escalate"):
            return "close"
        return "execute"
    return "intake"


def route_after_policy(state: TicketState) -> str:
    """Route after policy_check node based on the most restrictive policy decision."""
    decisions = state.get("policy_decisions", [])
    if not decisions:
        return "escalate_close"

    tiers = [d.get("tier", "forbidden") for d in decisions]
    if "forbidden" in tiers:
        return "escalate_close"
    elif "approval" in tiers:
        return "approval_interrupt"
    elif all(t == "auto" for t in tiers):
        return "execute"
    else:
        return "escalate_close"


def route_after_identity(state: TicketState) -> str:
    """If identity not verified, block writes and escalate."""
    identity = state.get("identity", {})
    if identity and not identity.get("verified", False):
        return "escalate_close"
    return "gather_context"


def build_workflow(checkpointer=None):
    """
    Build and compile the ResolveOps LangGraph workflow.

    Args:
        checkpointer: LangGraph checkpointer (PostgresSaver for production,
                      MemorySaver for testing/in-memory)
    """
    graph = StateGraph(TicketState)

    # ── Add all 11 nodes (instrumented for timing & Langfuse spans) ──
    graph.add_node("intake", instrument_node("intake", intake_node))
    graph.add_node("classify", instrument_node("classify", classify_node))
    graph.add_node("verify_identity", instrument_node("verify_identity", verify_identity_node))
    graph.add_node("gather_context", instrument_node("gather_context", gather_context_node))
    graph.add_node("plan_action", instrument_node("plan_action", plan_action_node))
    graph.add_node("policy_check", instrument_node("policy_check", policy_check_node))
    graph.add_node("approval_interrupt", instrument_node("approval_interrupt", approval_interrupt_node))
    graph.add_node("execute", instrument_node("execute", execute_node))
    graph.add_node("verify_outcome", instrument_node("verify_outcome", verify_outcome_node))
    graph.add_node("draft_reply", instrument_node("draft_reply", draft_reply_node))
    graph.add_node("close", instrument_node("close", close_node))

    # ── Edges ──────────────────────────────────────────────────
    graph.add_conditional_edges(
        START,
        route_at_start,
        {
            "intake": "intake",
            "execute": "execute",
            "close": "close",
        }
    )

    graph.add_edge("intake", "classify")
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

    # After approval interrupt — workflow pauses here awaiting human decision
    graph.add_edge("approval_interrupt", END)

    # Execution pipeline
    graph.add_edge("execute", "verify_outcome")
    graph.add_edge("verify_outcome", "draft_reply")
    graph.add_edge("draft_reply", "close")
    graph.add_edge("close", END)

    # Compile with checkpointer
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    return graph.compile(**compile_kwargs)


_compiled_workflow = None


def get_compiled_workflow(checkpointer=None):
    """Retrieve or build the singleton compiled LangGraph workflow."""
    global _compiled_workflow
    if _compiled_workflow is None:
        if checkpointer is None:
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
        _compiled_workflow = build_workflow(checkpointer=checkpointer)
    return _compiled_workflow
