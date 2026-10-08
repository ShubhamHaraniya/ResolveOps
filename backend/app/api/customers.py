"""Customers API router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

router = APIRouter()


@router.get("/customers")
async def list_customers(
    plan: str | None = None,
    is_strategic: bool | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return {"customers": [], "total": 0, "page": page}


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    raise HTTPException(status_code=404, detail="Customer not found")
