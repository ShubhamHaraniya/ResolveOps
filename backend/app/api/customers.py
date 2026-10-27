"""Customers API: read-only views over the accounts and contacts tables."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, AccountPlan, Contact, Ticket
from app.db.session import get_db

router = APIRouter()


def _account_dict(a: Account, contacts: int = 0, tickets: int = 0) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "plan": a.plan.value if a.plan else None,
        "arr_cents": a.arr_cents,
        "is_strategic": a.is_strategic,
        "is_legal_hold": a.is_legal_hold,
        "csm_owner": a.csm_owner,
        "status": a.status,
        "contact_count": contacts,
        "ticket_count": tickets,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/customers")
async def list_customers(
    plan: str | None = None,
    is_strategic: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Account)
    if plan:
        try:
            query = query.where(Account.plan == AccountPlan(plan))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Unknown plan '{plan}'")
    if is_strategic is not None:
        query = query.where(Account.is_strategic == is_strategic)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (
        await db.execute(query.order_by(Account.name).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    ids = [a.id for a in rows]
    contact_counts: dict[str, int] = {}
    ticket_counts: dict[str, int] = {}
    if ids:
        contact_counts = dict(
            (await db.execute(
                select(Contact.account_id, func.count()).where(Contact.account_id.in_(ids)).group_by(Contact.account_id)
            )).all()
        )
        ticket_counts = dict(
            (await db.execute(
                select(Ticket.account_id, func.count()).where(Ticket.account_id.in_(ids)).group_by(Ticket.account_id)
            )).all()
        )

    return {
        "customers": [_account_dict(a, contact_counts.get(a.id, 0), ticket_counts.get(a.id, 0)) for a in rows],
        "total": total,
        "page": page,
    }


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, customer_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    contacts = (
        await db.execute(select(Contact).where(Contact.account_id == customer_id).order_by(Contact.email))
    ).scalars().all()
    ticket_count = (
        await db.execute(select(func.count()).select_from(Ticket).where(Ticket.account_id == customer_id))
    ).scalar() or 0
    data = _account_dict(account, len(contacts), ticket_count)
    data["contacts"] = [
        {"id": c.id, "email": c.email, "name": c.name, "role": c.role, "is_authorized": c.is_authorized}
        for c in contacts
    ]
    return data
