import asyncio
import uuid
from app.db.session import AsyncSessionLocal
from app.db.models import Ticket, TicketStatus, TicketCategory, TicketUrgency
from app.graph.runner import run_workflow_for_ticket

async def main():
    tid = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        t = Ticket(
            id=tid,
            requester_email="jane@acme.com",
            subject="Duplicate charge",
            body_html="I was charged twice for my Pro plan. Please refund $30.",
            category=TicketCategory.refund,
            urgency=TicketUrgency.medium,
            status=TicketStatus.open,
        )
        db.add(t)
        await db.commit()
    print("Ticket created:", tid)

    res = await run_workflow_for_ticket(tid)
    print("Workflow run status:", res.get("status"))
    print("Nodes executed:")
    for n in res.get("nodes", []):
        print(f"  {n['node']}: {n['status']} ({n.get('duration_ms')}ms)")

    # If awaiting approval, test approving
    if res.get("status") == "awaiting_approval":
        print("\nNow testing resume on approval...")
        approval_id = res["state"].get("approval_id")
        async with AsyncSessionLocal() as db:
            from app.db.models import Approval, ApprovalStatus
            from sqlalchemy import update
            await db.execute(update(Approval).where(Approval.id == approval_id).values(status=ApprovalStatus.approved))
            await db.commit()
        try:
            from services.gateway.gateway import _approvals
            if approval_id and approval_id in _approvals:
                _approvals[approval_id]["status"] = "approved"
        except Exception:
            pass

        res2 = await run_workflow_for_ticket(tid, run_id=res["run_id"], resume_approval=True, action_type="approve")
        print("After approval status:", res2.get("status"))
        for n in res2.get("nodes", []):
            print(f"  {n['node']}: {n['status']} ({n.get('duration_ms')}ms)")
        print("\nExecuted actions:")
        for ex in res2.get("state", {}).get("executed", []):
            print(f"  Tool: {ex['tool']}, Result: {ex.get('result')}")

if __name__ == "__main__":
    asyncio.run(main())
