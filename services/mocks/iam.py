"""
Mock IAM System
CRITICAL: Only viewer and member roles are grantable. Admin is always forbidden.
"""
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, field_validator
from seed_data import IAM_USERS, IAM_GRANTS, CONTACTS

app = FastAPI(title="Mock IAM", version="1.0.0")

_mfa_resets: list[dict] = []
_grants: dict = dict(IAM_GRANTS)  # copy


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-iam"}


@app.get("/users/{email}")
def get_user(email: str):
    if email not in IAM_USERS:
        raise HTTPException(status_code=404, detail=f"User {email} not found")
    return IAM_USERS[email]


@app.get("/grants")
def list_grants(account_id: str = Query(...)):
    return {"account_id": account_id, "grants": _grants.get(account_id, [])}


ALLOWED_ROLES = {"viewer", "member"}
FORBIDDEN_ROLES = {"admin", "prod-admin", "owner", "superuser", "root", "administrator"}


class GrantAccessRequest(BaseModel):
    account_id: str
    user_email: str
    role: str
    expiry_days: int = 30
    reason: str

    @field_validator("role")
    @classmethod
    def role_must_be_safe(cls, v: str) -> str:
        if v.lower() in FORBIDDEN_ROLES:
            raise ValueError(f"Role '{v}' is forbidden — only viewer and member are available")
        if v.lower() not in ALLOWED_ROLES:
            raise ValueError(f"Role '{v}' is not a valid role. Allowed: {ALLOWED_ROLES}")
        return v.lower()

    @field_validator("expiry_days")
    @classmethod
    def expiry_must_be_bounded(cls, v: int) -> int:
        if v > 30:
            raise ValueError("expiry_days cannot exceed 30")
        if v < 1:
            raise ValueError("expiry_days must be at least 1")
        return v


@app.post("/access-grants", status_code=201)
def grant_access(payload: GrantAccessRequest):
    """
    CRITICAL SECURITY:
    - Only 'viewer' and 'member' roles are accepted.
    - 'admin', 'prod-admin', and all privilege-escalation roles → 403.
    - This check is at the schema level (pydantic) AND the endpoint level.
    """
    # Double-check at endpoint level (defense in depth)
    if payload.role.lower() in FORBIDDEN_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"FORBIDDEN: Role '{payload.role}' is not available. "
                   f"Admin and privileged roles are never grantable via the agent."
        )

    from datetime import datetime, UTC, timedelta
    grant = {
        "id": f"GRANT-{len(_mfa_resets)+100}",
        "account_id": payload.account_id,
        "user_email": payload.user_email,
        "role": payload.role,
        "expiry_days": payload.expiry_days,
        "expires_at": (datetime.now(UTC) + timedelta(days=payload.expiry_days)).isoformat(),
        "status": "active",
        "reason": payload.reason,
    }
    if payload.account_id not in _grants:
        _grants[payload.account_id] = []
    _grants[payload.account_id].append(grant)
    return grant


class MFAResetRequest(BaseModel):
    email: str
    account_id: str
    reason: str


@app.post("/mfa-reset", status_code=201)
def reset_mfa(payload: MFAResetRequest):
    if payload.email not in IAM_USERS:
        raise HTTPException(status_code=404, detail=f"User {payload.email} not found")
    from datetime import datetime, UTC
    reset = {
        "id": f"MFA-RESET-{len(_mfa_resets)+1}",
        "email": payload.email,
        "account_id": payload.account_id,
        "status": "reset_sent",
        "reset_token": "mfa-reset-token-stub",
        "expires_at": (datetime.now(UTC).isoformat()),
        "reason": payload.reason,
    }
    _mfa_resets.append(reset)
    return reset


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
