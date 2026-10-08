export type ResolutionTier = "auto" | "approval" | "forbidden" | "escalated";
export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type TicketStatus = "open" | "in_progress" | "waiting_approval" | "resolved" | "blocked";

export interface CustomerInfo {
  id: string;
  name: string;
  domain: string;
  plan: "Starter" | "Growth" | "Enterprise";
  arr: number;
  is_strategic: boolean;
  is_legal_hold: boolean;
  owner: string;
  csm: string;
  verified_contact?: {
    email: string;
    name: string;
    role: string;
    is_verified: boolean;
    verification_method: string;
    confidence: number;
  };
}

export interface Invoice {
  id: string;
  number: string;
  amount: number;
  currency: string;
  status: "paid" | "open" | "refunded" | "disputed";
  issued_at: string;
}

export interface TicketMessage {
  id: string;
  sender_type: "customer" | "agent" | "system";
  sender_name: string;
  body: string;
  timestamp: string;
}

export interface RAGCitation {
  id: string;
  title: string;
  version: string;
  section: string;
  snippet: string;
  url: string;
  is_active: boolean;
}

export interface ProposedAction {
  tool: string;
  tier: ResolutionTier;
  policy_rule: string;
  policy_rule_name: string;
  arguments: Record<string, any>;
  args_hash: string;
  status: "pending_review" | "auto_executed" | "forbidden" | "executed" | "rejected";
  execution_result?: any;
}

export interface AIAnalysis {
  category: string;
  urgency: "low" | "medium" | "high" | "critical";
  sentiment: "positive" | "neutral" | "negative" | "frustrated";
  confidence: number;
  summary: string;
  key_entities: Record<string, string>;
  conflict_detected?: boolean;
  conflict_details?: string;
}

export interface Ticket {
  id: string;
  ticket_number: string;
  customer: CustomerInfo;
  requester_email: string;
  subject: string;
  body: string;
  category: string;
  priority: TicketPriority;
  tier: ResolutionTier;
  status: TicketStatus;
  confidence: number;
  risk_flags: string[];
  created_at: string;
  updated_at: string;
  messages: TicketMessage[];
  invoices?: Invoice[];
  ai_analysis?: AIAnalysis;
  rag_citations?: RAGCitation[];
  proposed_action?: ProposedAction;
  run_id?: string;
}

export interface ApprovalItem {
  id: string;
  ticket_id: string;
  ticket_number: string;
  customer_name: string;
  action_summary: string;
  tool: string;
  args: Record<string, any>;
  args_hash: string;
  amount?: number;
  risk_badge: "Low" | "Medium" | "High" | "Critical";
  policy_rule: string;
  approver_role: string;
  category: "Financial" | "Security" | "Low Confidence" | "Conflicts";
  status: "pending" | "approved" | "rejected" | "expired" | "escalated";
  created_at: string;
  expires_at: string;
  is_stale?: boolean;
  stale_reason?: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  run_id: string;
  ticket_id: string;
  actor_type: "agent" | "human" | "system" | "gateway";
  actor_id: string;
  event: string;
  tool?: string;
  args_hash?: string;
  args_redacted?: Record<string, any>;
  policy_rule?: string;
  policy_version?: string;
  idempotency_key?: string;
  result_status: "SUCCESS" | "BLOCKED" | "INTERRUPTED" | "ERROR" | "INFO";
  trace_id?: string;
  prev_hash: string;
  row_hash: string;
}

export interface TraceNode {
  id: string;
  name: string;
  status: "completed" | "interrupted" | "failed" | "skipped" | "running";
  latency_ms: number;
  model?: string;
  provider?: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  estimated_cost?: number;
  input_summary?: string;
  output_summary?: string;
}

export interface TraceRun {
  run_id: string;
  ticket_id: string;
  ticket_number: string;
  status: "completed" | "interrupted" | "failed";
  started_at: string;
  ended_at: string;
  total_duration_ms: number;
  total_tokens: number;
  total_cost: number;
  nodes: TraceNode[];
}

export interface ServiceHealth {
  name: string;
  status: "healthy" | "degraded" | "unreachable";
  latency_ms: number;
  last_check: string;
}

export interface DemoScenario {
  id: string;
  name: string;
  description: string;
  expected_outcome: string;
  badge_color: "blue" | "red" | "amber" | "emerald" | "purple";
  ticket_id: string;
}
