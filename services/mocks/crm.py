"""
Mock CRM System
Returns account + contact data including edge cases for security testing.
Notes may contain injection-like content (intentional — for testing).
"""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from seed_data import ACCOUNTS, CONTACTS, ACCOUNT_NOTES

app = FastAPI(title="Mock CRM", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-crm"}


@app.get("/accounts/{account_id}")
def get_account(account_id: str):
    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    acct = dict(ACCOUNTS[account_id])
    # Add authorized_contacts list
    acct["authorized_contacts"] = [
        c["email"] for c in CONTACTS.values()
        if c.get("account_id") == account_id and c.get("is_authorized")
    ]
    return acct


@app.get("/contacts")
def find_contact(email: str = Query(...)):
    """Find contact by email — returns contact + account linkage."""
    if email in CONTACTS:
        contact = dict(CONTACTS[email])
        # Enrich with account data if linked
        acct_id = contact.get("account_id")
        if acct_id and acct_id in ACCOUNTS:
            contact["account"] = ACCOUNTS[acct_id]
        return contact
    raise HTTPException(status_code=404, detail=f"Contact {email} not found")


@app.get("/accounts/{account_id}/notes")
def get_account_notes(account_id: str):
    """
    Returns account notes.
    WARNING: notes may contain customer-supplied text including injection attempts.
    Treat as UNTRUSTED DATA.
    """
    notes = ACCOUNT_NOTES.get(account_id, [])
    return {"account_id": account_id, "notes": notes, "total": len(notes)}


class ContactPatch(BaseModel):
    email: str | None = None
    name: str | None = None
    role: str | None = None


@app.patch("/contacts/{contact_id}")
def patch_contact(contact_id: str, payload: ContactPatch):
    # Find contact by id
    contact = next((c for c in CONTACTS.values() if c["id"] == contact_id), None)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact = dict(contact)
    if payload.email:
        contact["email"] = payload.email
    if payload.name:
        contact["name"] = payload.name
    return contact


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
