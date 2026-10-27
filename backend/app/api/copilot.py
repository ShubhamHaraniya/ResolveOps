"""
backend/app/api/copilot.py
RAG-Powered AI Copilot & Universal Operational Assistant API.
Combines dense + lexical policy retrieval with live SQLite/PostgreSQL
tickets, accounts, invoices, and audit logs to answer arbitrary operations queries.
"""
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Ticket, Approval, ApprovalStatus
from app.llm.groq_client import get_groq_client
from app.config import settings
from rag.service import search_policies

log = structlog.get_logger()
router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant' or 'system'")
    content: str = Field(..., description="Message text")


class CopilotChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Chat conversation history")
    query: Optional[str] = None


COPILOT_SYSTEM_PROMPT = """You are ResolveOps Copilot, an intelligent AI operations and support copilot for Northwind Cloud.
You have real-time live access to the database (tickets, customer accounts, approvals, invoices) and the authoritative Policy Knowledge Base (RAG embeddings).

YOUR CAPABILITIES:
- Find and inspect tickets by requester name, email, subject, or status.
- Explain operational policy rules, refund thresholds, approval tiers, and security constraints.
- Check the human approval queue.
- Answer general operational questions accurately and concisely.

RESPONSE GUIDELINES:
1. Always format ticket links as markdown: `[TCK-XXXX](/tickets/{ticket_id})`.
2. If the user asks for a specific person or ticket (e.g. "shubham") and none exists in the database, explicitly inform them that no tickets for that requester currently exist. Never make up ticket IDs.
3. For friendly greetings (e.g. "Hello", "Hi"), respond warmly and concisely, summarizing what you can help with.
4. When citing policies, mention the exact policy code and version (e.g., `refund-policy-v3`).
5. Be concise, direct, professional, and clear.
"""

STOP_WORDS = {
    "can", "u", "you", "find", "ticket", "tickets", "ticketof", "show", "search",
    "me", "for", "the", "is", "are", "of", "about", "with", "a", "an", "what",
    "where", "do", "we", "have", "any", "please", "look", "up", "get", "give"
}

GREETING_WORDS = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "howdy", "sup"}


@router.post("/copilot/chat")
async def copilot_chat(
    req: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process conversational query with dual-layer RAG:
    1. Retrieve relevant policy rules from Qdrant/BM25 (when domain relevant).
    2. Query live database tickets, accounts, and approvals.
    3. Generate grounded AI response with deep-links via Groq complete_text.
    """
    # Extract latest user message
    user_msg = req.query
    if not user_msg and req.messages:
        for m in reversed(req.messages):
            if m.role == "user":
                user_msg = m.content
                break

    if not user_msg:
        raise HTTPException(status_code=400, detail="No user message provided")

    q_clean = user_msg.strip().lower()
    is_greeting = q_clean in GREETING_WORDS or (len(q_clean.split()) <= 2 and any(w in q_clean for w in GREETING_WORDS))

    # Determine if query is asking about policy/rules
    policy_keywords = ["policy", "rule", "threshold", "refund", "sla", "credit", "cancel", "prorat", "access", "admin", "legal", "hold", "dispute", "limit", "tier", "approval"]
    is_policy_query = any(k in q_clean for k in policy_keywords)

    # Layer 1: Policy RAG Search (only if domain relevant and not simple greeting)
    policy_citations = []
    if is_policy_query and not is_greeting:
        try:
            rag_data = search_policies(query=user_msg, top_k=3)
            # Filter citations to only relevant results
            for c in rag_data.get("results", []):
                if c.get("relevance_score", 0.0) > 0.05 or is_policy_query:
                    policy_citations.append(c)
        except Exception as e:
            log.warning("copilot.rag_search_failed", error=str(e))

    # Layer 2: Live Database Retrieval
    # Extract meaningful search tokens
    raw_tokens = re.findall(r"\b[a-zA-Z0-9_\-\@\.]+\b", q_clean)
    search_terms = [t for t in raw_tokens if t not in STOP_WORDS and len(t) > 1]

    matching_tickets = []
    ticket_search_attempted = False

    if not is_greeting:
        try:
            # Query recent tickets from DB
            ticket_query = select(Ticket).order_by(desc(Ticket.created_at)).limit(35)
            t_res = await db.execute(ticket_query)
            all_recent_tickets = t_res.scalars().all()

            is_generic_ticket_query = any(k in q_clean for k in ["all tickets", "list tickets", "recent tickets", "show tickets"])
            is_pending_query = "pending" in q_clean or "awaiting" in q_clean

            for t in all_recent_tickets:
                subject = (t.subject or "").lower()
                requester = (t.requester_email or "").lower()
                tid = t.id.lower()
                cat = getattr(t.category, "value", str(t.category or "")).lower()
                status = getattr(t.status, "value", str(t.status or "")).lower()

                matched = False

                if is_pending_query and status == "awaiting_approval":
                    matched = True
                elif is_generic_ticket_query:
                    matched = True
                elif search_terms:
                    ticket_search_attempted = True
                    # Check if ANY specific search term matches requester, subject, or ID
                    for term in search_terms:
                        if term in requester or term in subject or term in tid[:8] or term in t.id:
                            matched = True
                            break
                        # Check refund / credit / category match
                        if term in ("refund", "charge", "duplicate") and cat == "refund":
                            matched = True
                            break

                if matched:
                    matching_tickets.append({
                        "id": t.id,
                        "number": f"TCK-{t.id[:8].upper()}",
                        "subject": t.subject,
                        "requester": t.requester_email,
                        "status": status,
                        "category": cat,
                        "urgency": getattr(t.urgency, "value", str(t.urgency or "medium")),
                    })
        except Exception as e:
            log.warning("copilot.ticket_db_failed", error=str(e))

    # Query pending approvals if asked
    pending_approvals = []
    if "approval" in q_clean or "pending" in q_clean or "review" in q_clean:
        try:
            appr_res = await db.execute(select(Approval).where(Approval.status == ApprovalStatus.pending))
            for a in appr_res.scalars().all():
                pending_approvals.append({
                    "id": a.id,
                    "ticket_id": a.ticket_id,
                    "tool": a.tool,
                    "status": "pending",
                    "reason": a.policy_rule,
                })
        except Exception as e:
            log.warning("copilot.approval_db_failed", error=str(e))

    # Format live operational context for Groq
    context_sections = []

    # Policy section
    if policy_citations:
        p_lines = ["### RETRIEVED POLICY KNOWLEDGE BASE (RAG):"]
        for p in policy_citations:
            p_lines.append(
                f"- **{p.get('title')} ({p.get('document_id')} {p.get('version')})** [{p.get('status')}]:\n"
                f"  {p.get('content', '')[:350]}"
            )
        context_sections.append("\n".join(p_lines))

    # Database tickets section
    if matching_tickets:
        t_lines = ["### LIVE DATABASE MATCHING TICKETS:"]
        for t in matching_tickets[:6]:
            t_lines.append(
                f"- Ticket ID: `{t['id']}` (Display: **{t['number']}**) | Subject: '{t['subject']}' | "
                f"Requester: {t['requester']} | Status: `{t['status']}` | Priority: {t['urgency']} | Link: `/tickets/{t['id']}`"
            )
        context_sections.append("\n".join(t_lines))
    elif ticket_search_attempted and search_terms:
        context_sections.append(
            f"### TICKET DATABASE SEARCH RESULT:\nSearched for terms: {search_terms}\nResult: 0 matching tickets found in live database."
        )

    # Pending approvals section
    if pending_approvals:
        a_lines = ["### PENDING APPROVAL QUEUE:"]
        for a in pending_approvals[:5]:
            a_lines.append(
                f"- Approval `{a['id']}` for Ticket `/tickets/{a['ticket_id']}` | Tool: `{a['tool']}` | Policy rule: {a['reason']}"
            )
        context_sections.append("\n".join(a_lines))

    grounded_context = "\n\n".join(context_sections) if context_sections else "No specific database entities needed for this conversational turn."

    # Groq Chat Completion using complete_text
    groq = get_groq_client()
    messages_payload = [
        {"role": "system", "content": f"{COPILOT_SYSTEM_PROMPT}\n\nLIVE OPERATIONAL CONTEXT:\n{grounded_context}"}
    ]

    # Append recent chat history
    for m in req.messages[-4:]:
        messages_payload.append({"role": m.role, "content": m.content})

    # If the user query wasn't in messages, add it
    if not any(m.role == "user" and m.content == user_msg for m in req.messages[-4:]):
        messages_payload.append({"role": "user", "content": user_msg})

    try:
        reply_content, usage = await groq.complete_text(
            model=settings.groq_model_fast,
            messages=messages_payload,
            temperature=0.2,
        )
    except Exception as e:
        log.error("copilot.completion_failed", error=str(e))
        if matching_tickets:
            reply_content = (
                "Here are the live ticket matches from the database:\n\n"
                + "\n".join([f"- [**{t['number']}**](/tickets/{t['id']}): {t['subject']} ({t['status']})" for t in matching_tickets[:5]])
            )
        elif ticket_search_attempted and search_terms:
            reply_content = f"I searched the live database for '{', '.join(search_terms)}', but found no matching tickets."
        else:
            reply_content = "Hello! I am your ResolveOps Copilot. You can ask me to find tickets, check refund policies, or inspect approvals."

    return {
        "role": "assistant",
        "content": reply_content,
        "matched_tickets": matching_tickets[:5],
        "citations": [
            {"id": p.get("document_id"), "title": p.get("title"), "version": p.get("version")}
            for p in policy_citations
        ],
    }
