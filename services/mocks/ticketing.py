"""
Mock Ticketing System
Serves realistic ticket data including HTML, forwarded emails, and injection test cases.
"""
import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from seed_data import TICKETS, ACCOUNTS

app = FastAPI(title="Mock Ticketing", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-ticketing"}


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    if ticket_id not in TICKETS:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    ticket = dict(TICKETS[ticket_id])
    # Enrich with account info
    acct_id = ticket.get("account_id")
    if acct_id and acct_id in ACCOUNTS:
        ticket["account"] = ACCOUNTS[acct_id]
    return ticket


@app.get("/tickets")
def list_tickets(requester: str = Query(None), account_id: str = Query(None), status: str = Query(None)):
    results = list(TICKETS.values())
    if requester:
        results = [t for t in results if t.get("requester_email") == requester]
    if account_id:
        results = [t for t in results if t.get("account_id") == account_id]
    if status:
        results = [t for t in results if t.get("status") == status]
    return {"tickets": results, "total": len(results)}


class CommentRequest(BaseModel):
    body: str
    is_internal: bool = True
    author: str = "agent@resolveops"


@app.post("/tickets/{ticket_id}/comments", status_code=201)
def add_comment(ticket_id: str, payload: CommentRequest):
    if ticket_id not in TICKETS:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {
        "id": f"MSG-{ticket_id}-{os.urandom(4).hex()}",
        "ticket_id": ticket_id,
        "body": payload.body,
        "is_internal": payload.is_internal,
        "author": payload.author,
        "created_at": "2026-10-08T13:00:00Z",
    }


class TicketPatch(BaseModel):
    status: str | None = None
    tags: list[str] | None = None
    category: str | None = None


@app.patch("/tickets/{ticket_id}")
def patch_ticket(ticket_id: str, payload: TicketPatch):
    if ticket_id not in TICKETS:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = dict(TICKETS[ticket_id])
    if payload.status:
        ticket["status"] = payload.status
    if payload.tags:
        ticket["tags"] = payload.tags
    if payload.category:
        ticket["category"] = payload.category
    return ticket


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
