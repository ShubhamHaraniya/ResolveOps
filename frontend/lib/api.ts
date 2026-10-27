/**
 * frontend/lib/api.ts
 * Real API client connecting ResolveOps Next.js frontend to FastAPI backend.
 */

const API_BASE = typeof window !== "undefined" ? "/api" : (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api");

export interface CreateTicketPayload {
  requester_email: string;
  subject: string;
  body: string;
  category?: string;
  priority?: string;
  account_id?: string;
  is_authorized_contact?: boolean;
  metadata?: Record<string, any>;
}

export interface TicketRunResponse {
  ticket_id: string;
  run_id?: string;
  status: string;
}

export interface WorkflowNodeStatus {
  node: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped" | "paused";
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error?: string | null;
  details?: Record<string, any>;
}

export interface LiveTicketDetail {
  ticket: {
    id: string;
    ticket_number: string;
    requester_email: string;
    subject: string;
    body_html: string;
    category: string;
    urgency: string;
    status: string;
    risk_flags: string[];
    sentiment?: string | null;
    created_at: string;
    account_id?: string | null;
  };
  latest_run?: {
    run_id: string;
    ticket_id: string;
    status: string;
    started_at: string;
    completed_at?: string | null;
    error?: string | null;
    nodes: WorkflowNodeStatus[];
    state?: Record<string, any>;
  } | null;
  messages: Array<{
    id: string;
    sender_type: "customer" | "agent" | "system";
    sender_name: string;
    body: string;
    timestamp: string;
  }>;
  pending_approval?: {
    id: string;
    tool: string;
    policy_rule: string;
    approver_role: string;
    args_redacted: Record<string, any>;
    args_full?: Record<string, any>;
    status: string;
    created_at: string;
    expires_at?: string;
    reasoning?: string;
  } | null;
}

export async function fetchTicketsList(status?: string, limit = 50) {
  const url = new URL(`${API_BASE}/tickets`, typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:3000");
  if (status && status !== "all") url.searchParams.set("status", status);
  url.searchParams.set("limit", limit.toString());

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch tickets: ${res.statusText}`);
  }
  return res.json();
}

export async function createTicketAndRun(payload: CreateTicketPayload): Promise<TicketRunResponse> {
  const res = await fetch(`${API_BASE}/tickets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to create ticket: ${errorText || res.statusText}`);
  }
  return res.json();
}

export async function fetchTicketDetail(ticketId: string): Promise<LiveTicketDetail> {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ticket ${ticketId}: ${res.statusText}`);
  }
  return res.json();
}

export async function runTicketWorkflow(ticketId: string): Promise<TicketRunResponse> {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/run`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Failed to trigger run for ${ticketId}`);
  }
  return res.json();
}

export async function fetchRunState(runId: string) {
  const res = await fetch(`${API_BASE}/runs/${runId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch run ${runId}`);
  }
  return res.json();
}

export async function approveTicketAction(
  approvalId: string,
  reviewerId = "support_lead_01",
  notes?: string
) {
  const res = await fetch(`${API_BASE}/approvals/${approvalId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_id: reviewerId, notes }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Approval failed: ${err || res.statusText}`);
  }
  return res.json();
}

export async function rejectTicketAction(
  approvalId: string,
  reason: string,
  reviewerId = "support_lead_01"
) {
  const res = await fetch(`${API_BASE}/approvals/${approvalId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_id: reviewerId, reason }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Rejection failed: ${err || res.statusText}`);
  }
  return res.json();
}

export async function editTicketAction(
  approvalId: string,
  updatedArgs: Record<string, any>,
  reason = "Edited by reviewer",
  reviewerId = "support_lead_01"
) {
  const res = await fetch(`${API_BASE}/approvals/${approvalId}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_id: reviewerId, updated_args: updatedArgs, reason }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Edit failed: ${err || res.statusText}`);
  }
  return res.json();
}

export async function escalateTicketAction(
  approvalId: string,
  reason: string,
  escalateTo = "vp_support",
  reviewerId = "support_lead_01"
) {
  const res = await fetch(`${API_BASE}/approvals/${approvalId}/escalate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_id: reviewerId, escalate_to: escalateTo, reason }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Escalation failed: ${err || res.statusText}`);
  }
  return res.json();
}
