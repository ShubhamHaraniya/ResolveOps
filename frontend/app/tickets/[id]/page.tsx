"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Play,
  RotateCw,
  FileText,
  Hash,
  User,
  Bot,
  Building,
  GitFork,
  Edit3,
  Lock,
  PauseCircle,
  Check,
  X,
  ArrowUpRight,
  Database,
  Cpu,
  RefreshCw,
  Send,
  CornerDownRight,
  MessageSquare,
} from "lucide-react";
import { TierBadge, PriorityBadge, StatusBadge } from "@/components/Badges";
import { timeAgo } from "@/lib/utils";
import {
  fetchTicketDetail,
  runTicketWorkflow,
  approveTicketAction,
  rejectTicketAction,
  editTicketAction,
  escalateTicketAction,
  WorkflowNodeStatus,
} from "@/lib/api";

const NODE_LABELS: Record<string, string> = {
  intake: "Intake",
  classify: "Classification",
  verify_identity: "Identity Verification",
  gather_context: "Context Gathering",
  plan_action: "Groq Planning",
  policy_check: "Policy Check",
  approval_interrupt: "Waiting for Approval",
  execute: "Execution",
  verify_outcome: "Verification",
  draft_reply: "Draft Reply",
  close: "Ticket Finalize",
};

export default function TicketLiveDetailPage() {
  const params = useParams();
  const ticketId = (params?.id as string) || "";

  const [ticketData, setTicketData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Modals for Review Actions
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editArgsJson, setEditArgsJson] = useState("");
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [escalateModalOpen, setEscalateModalOpen] = useState(false);
  const [escalateReason, setEscalateReason] = useState("");

  // Multi-Turn Reply states
  const [replyText, setReplyText] = useState("");
  const [replySender, setReplySender] = useState<"customer" | "agent">("customer");
  const [isInternalNote, setIsInternalNote] = useState(false);
  const [sendingReply, setSendingReply] = useState(false);

  const handleSendReply = async () => {
    if (!replyText.trim() || sendingReply) return;
    setSendingReply(true);
    try {
      const res = await fetch(`/api/tickets/${ticketId}/reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sender_type: replySender,
          body: replyText,
          is_internal: isInternalNote,
        }),
      });
      if (res.ok) {
        setReplyText("");
        await loadTicketData(false);
      } else {
        alert("Failed to submit reply");
      }
    } catch (err: any) {
      alert("Error submitting reply: " + err.message);
    } finally {
      setSendingReply(false);
    }
  };

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch real data from backend
  const loadTicketData = async (showLoadingSpinner = false) => {
    if (!ticketId) return;
    if (showLoadingSpinner) setLoading(true);

    try {
      const res = await fetchTicketDetail(ticketId);
      setTicketData(res);
      setError(null);
    } catch (err: any) {
      console.error("Failed to load ticket:", err);
      setError(err.message || "Failed to load live ticket state");
    } finally {
      if (showLoadingSpinner) setLoading(false);
    }
  };

  useEffect(() => {
    loadTicketData(true);

    // Short-interval polling (1000ms) for real-time live execution updates
    pollIntervalRef.current = setInterval(() => {
      loadTicketData(false);
    }, 1000);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [ticketId]);

  // Check if run is currently active
  const runStatus = ticketData?.run?.status || ticketData?.status;
  const isWorkflowActive = runStatus === "running";

  // Re-run workflow handler
  const handleTriggerRun = async () => {
    setActionLoading(true);
    try {
      await runTicketWorkflow(ticketId);
      await loadTicketData(false);
    } catch (err: any) {
      alert("Failed to run workflow: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Approval handlers
  const handleApprove = async () => {
    const apprId = ticketData?.approval?.id;
    if (!apprId) return;

    setActionLoading(true);
    try {
      await approveTicketAction(apprId, "support_lead_01", "Approved via live test dashboard");
      await loadTicketData(false);
    } catch (err: any) {
      alert("Approval execution error: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenEdit = () => {
    const args = ticketData?.approval?.args_full || ticketData?.approval?.args_redacted || {};
    setEditArgsJson(JSON.stringify(args, null, 2));
    setEditModalOpen(true);
  };

  const handleConfirmEdit = async () => {
    const apprId = ticketData?.approval?.id;
    if (!apprId) return;

    let parsed: Record<string, any>;
    try {
      parsed = JSON.parse(editArgsJson);
    } catch {
      alert("Invalid JSON arguments");
      return;
    }

    setActionLoading(true);
    try {
      await editTicketAction(apprId, parsed, "Adjusted arguments by support lead");
      setEditModalOpen(false);
      await loadTicketData(false);
    } catch (err: any) {
      alert("Edit error: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmReject = async () => {
    const apprId = ticketData?.approval?.id;
    if (!apprId) return;

    setActionLoading(true);
    try {
      await rejectTicketAction(apprId, rejectReason || "Rejected by Support Lead review");
      setRejectModalOpen(false);
      await loadTicketData(false);
    } catch (err: any) {
      alert("Rejection error: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmEscalate = async () => {
    const apprId = ticketData?.approval?.id;
    if (!apprId) return;

    setActionLoading(true);
    try {
      await escalateTicketAction(apprId, escalateReason || "Escalated for VP review");
      setEscalateModalOpen(false);
      await loadTicketData(false);
    } catch (err: any) {
      alert("Escalation error: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !ticketData) {
    return (
      <div className="p-12 text-center text-xs text-slate-500 flex flex-col items-center justify-center gap-3">
        <RotateCw className="w-6 h-6 animate-spin text-blue-600" />
        <span>Loading live ticket state from database...</span>
      </div>
    );
  }

  if (error && !ticketData) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs">
          <p className="font-semibold">Unable to load ticket</p>
          <p className="mt-1">{error}</p>
        </div>
        <Link
          href="/tickets"
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg bg-slate-900 text-white"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Tickets
        </Link>
      </div>
    );
  }

  const {
    ticket_number,
    subject,
    requester_email,
    category,
    priority,
    status,
    tier,
    confidence,
    risk_flags = [],
    created_at,
    customer = {},
    messages = [],
    workflow_progress = [],
    ai_analysis = {},
    identity = {},
        retrieved_knowledge = [],
    policy_decision,
        approval,
    execution_result = [],
    run,
  } = ticketData || {};

  const isAwaitingApproval = status === "awaiting_approval" || approval?.status === "pending";

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6">
      {/* ── SECTION 1: TICKET HEADER & CONTROLS ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200 bg-white p-5 rounded-2xl shadow-xs">
        <div className="flex items-start gap-4">
          <Link
            href="/tickets"
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors shrink-0"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-base font-bold text-slate-900">
                {ticket_number || `TCK-${ticketId.slice(0, 8).toUpperCase()}`}
              </span>
              <TierBadge tier={tier || "auto"} />
              <PriorityBadge priority={priority || "medium"} />
              <StatusBadge status={status || "open"} />
              {risk_flags?.includes("identity_mismatch") && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                  IDENTITY MISMATCH
                </span>
              )}
              {risk_flags?.includes("amount_mismatch") && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-300">
                  AMOUNT MISMATCH
                </span>
              )}
              {(risk_flags?.includes("injection_suspected") || risk_flags?.includes("prompt_injection_suspected")) && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-800 border border-red-300">
                  INJECTION DETECTED
                </span>
              )}
              {isWorkflowActive && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-100 text-blue-800 animate-pulse border border-blue-200">
                  <RotateCw className="w-3 h-3 animate-spin" />
                  Agent Running
                </span>
              )}
            </div>
            <h1 className="text-base font-semibold text-slate-800 mt-1">{subject}</h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Requester: <span className="text-slate-700 font-semibold">{requester_email}</span> • Created {timeAgo(created_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => loadTicketData(true)}
            className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Sync</span>
          </button>

          <button
            onClick={handleTriggerRun}
            disabled={actionLoading || isWorkflowActive}
            id="run-agent-btn"
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:bg-blue-300 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-all"
          >
            {actionLoading ? (
              <>
                <RotateCw className="w-3.5 h-3.5 animate-spin" />
                <span>Running Agent...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>{run ? "Re-run Agent" : "Run Agent"}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── RUN ERROR BANNER (e.g. MISSING API KEY) ── */}
      {run?.error && (
        <div className="bg-red-50 border-2 border-red-300 rounded-2xl p-4 flex items-start gap-3 shadow-xs">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-xs">
            <h3 className="font-bold text-red-900 text-sm">Agent Workflow Halted</h3>
            <p className="text-red-700 mt-1 font-mono text-[12px] bg-red-100/70 p-2 rounded-lg border border-red-200">
              {run.error}
            </p>
            {run.error.includes("GROQ_API_KEY") && (
              <p className="text-slate-600 mt-2 text-[12px]">
                To run live AI completions, open your root <code className="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-slate-800">.env</code> file, set <code className="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-slate-800">GROQ_API_KEY=gsk_...</code>, and click <strong>Re-run Agent</strong>.
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── SECTION 9 & 10: WORKFLOW PROGRESS & APPROVAL HERO (TOP PRIORITY) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Live LangGraph Workflow Timeline */}
        <div className="lg:col-span-7 space-y-6">
          {/* WORKFLOW PROGRESS SECTION */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <GitFork className="w-4 h-4 text-blue-600" />
                <h2 className="text-sm font-bold text-slate-900">LangGraph Workflow Progress</h2>
              </div>
              <span className="text-[11px] font-mono text-slate-400">
                Run ID: {run?.run_id ? run.run_id.slice(0, 8) + "..." : "Initial"}
              </span>
            </div>

            <div className="mt-4 space-y-2.5">
              {workflow_progress.length === 0 ? (
                <div className="text-center py-6 text-xs text-slate-400">
                  Agent run not started yet. Click &quot;Run Agent&quot; to execute workflow.
                </div>
              ) : (
                workflow_progress.map((node: WorkflowNodeStatus, idx: number) => {
                  const nodeName = NODE_LABELS[node.node] || node.node;
                  const isDone = node.status === "completed";
                  const isRunning = node.status === "running";
                  const isPaused = node.status === "paused";
                  const isFailed = node.status === "failed";
                  const isSkipped = node.status === "skipped";

                  return (
                    <div
                      key={node.node || idx}
                      className={`p-3 rounded-xl border flex items-center justify-between transition-all ${
                        isRunning
                          ? "bg-blue-50/70 border-blue-300 ring-1 ring-blue-400 shadow-xs"
                          : isPaused
                          ? "bg-amber-50/70 border-amber-300 ring-1 ring-amber-400 shadow-xs"
                          : isDone
                          ? "bg-emerald-50/40 border-emerald-200"
                          : isFailed
                          ? "bg-red-50/60 border-red-200"
                          : "bg-slate-50/50 border-slate-200 text-slate-400"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="shrink-0">
                          {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                          {isRunning && <RotateCw className="w-4 h-4 text-blue-600 animate-spin" />}
                          {isPaused && <PauseCircle className="w-4 h-4 text-amber-600 animate-pulse" />}
                          {isFailed && <XCircle className="w-4 h-4 text-red-600" />}
                          {isSkipped && <div className="w-4 h-4 rounded-full border-2 border-slate-300" />}
                          {node.status === "pending" && (
                            <div className="w-4 h-4 rounded-full border-2 border-slate-300" />
                          )}
                        </div>

                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs text-slate-900">{nodeName}</span>
                            <span
                              className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-semibold uppercase ${
                                isDone
                                  ? "bg-emerald-100 text-emerald-800"
                                  : isRunning
                                  ? "bg-blue-100 text-blue-800"
                                  : isPaused
                                  ? "bg-amber-100 text-amber-800"
                                  : isFailed
                                  ? "bg-red-100 text-red-800"
                                  : "bg-slate-200 text-slate-600"
                              }`}
                            >
                              {node.status}
                            </span>
                          </div>
                          {node.error && (
                            <p className="text-[11px] text-red-600 mt-0.5">{node.error}</p>
                          )}
                        </div>
                      </div>

                      <div className="text-right text-[11px] font-mono text-slate-500">
                        {node.duration_ms !== null && node.duration_ms !== undefined && (
                          <div className="font-medium text-slate-700">{node.duration_ms.toFixed(1)}ms</div>
                        )}
                        {node.completed_at && (
                          <div className="text-[10px] text-slate-400">
                            {new Date(node.completed_at).toLocaleTimeString()}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* SECTION 4: CONVERSATION STREAM */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <FileText className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-900">Conversation & Ticket Body</h2>
            </div>

            <div className="space-y-3">
              {messages.map((m: any, idx: number) => {
                const isCustomer = m.role === "customer" || m.sender_type === "customer";
                const isSystem = m.role === "system" || m.sender_type === "system";

                return (
                  <div
                    key={m.id || idx}
                    className={`p-4 rounded-xl border text-xs ${
                      isCustomer
                        ? "bg-slate-50 border-slate-200 text-slate-800"
                        : isSystem
                        ? "bg-purple-50/50 border-purple-200 text-purple-900"
                        : "bg-blue-50/50 border-blue-200 text-slate-900"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5 font-semibold">
                      <div className="flex items-center gap-1.5">
                        {isCustomer ? (
                          <User className="w-3.5 h-3.5 text-slate-500" />
                        ) : isSystem ? (
                          <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
                        ) : (
                          <Bot className="w-3.5 h-3.5 text-blue-600" />
                        )}
                        <span>{m.author || (isCustomer ? requester_email : "ResolveOps Agent")}</span>
                        {m.is_internal && (
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 font-normal">
                            INTERNAL NOTE
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {timeAgo(m.created_at || m.timestamp)}
                      </span>
                    </div>
                    <div className="whitespace-pre-wrap font-sans text-xs text-slate-700 leading-relaxed">
                      {m.body}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* MULTI-TURN REPLY BOX */}
            <div className="pt-4 border-t border-slate-100 space-y-3 bg-slate-50/60 p-4 rounded-xl border border-slate-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-blue-600" />
                  <span className="text-xs font-bold text-slate-800">
                    Send Multi-Turn Customer Reply / Follow-up
                  </span>
                </div>

                <div className="flex items-center gap-1.5 bg-slate-200/80 p-0.5 rounded-lg text-[11px]">
                  <button
                    type="button"
                    onClick={() => {
                      setReplySender("customer");
                      setIsInternalNote(false);
                    }}
                    className={`px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                      replySender === "customer"
                        ? "bg-white text-blue-700 shadow-2xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Customer Follow-Up
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setReplySender("agent");
                      setIsInternalNote(true);
                    }}
                    className={`px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                      replySender === "agent"
                        ? "bg-white text-amber-700 shadow-2xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Internal Note
                  </button>
                </div>
              </div>

              {replySender === "customer" && (
                <div className="text-[11px] text-blue-700 bg-blue-50/70 p-2 rounded-lg border border-blue-100 flex items-center gap-1.5">
                  <CornerDownRight className="w-3.5 h-3.5 shrink-0" />
                  <span>
                    Sending as Customer re-activates the LangGraph agent to generate a fresh plan with conversational memory of this entire thread.
                  </span>
                </div>
              )}

              {/* Quick suggestion chips */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {[
                  "Thanks, but can you refund $50 instead?",
                  "Please also prorate my subscription cancellation.",
                  "Can you check invoice INV-2026-003 status?",
                  "I want to escalate this to a supervisor.",
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setReplyText(chip)}
                    className="text-[10px] bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50 text-slate-600 px-2 py-1 rounded-md transition-colors text-left cursor-pointer"
                  >
                    &quot;{chip}&quot;
                  </button>
                ))}
              </div>

              <div className="relative">
                <textarea
                  rows={3}
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder={
                    replySender === "customer"
                      ? "Type customer follow-up message (e.g. 'Can we also credit my account?')..."
                      : "Type internal agent observation or supervisor guidance..."
                  }
                  className="w-full text-xs p-3 rounded-lg border border-slate-200 focus:outline-hidden focus:ring-1 focus:ring-blue-500 bg-white leading-relaxed resize-none"
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleSendReply}
                  disabled={sendingReply || !replyText.trim()}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white flex items-center gap-1.5 shadow-xs cursor-pointer transition-colors"
                >
                  <Send className={`w-3.5 h-3.5 ${sendingReply ? "animate-pulse" : ""}`} />
                  <span>{sendingReply ? "Sending & Running Agent..." : "Send Reply & Resume Workflow"}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Approval Box, Policy Decision, AI Analysis, Context */}
        <div className="lg:col-span-5 space-y-6">
          {/* SECTION 10: APPROVAL REQUIRED BOX (HERO ALERT) */}
          {isAwaitingApproval && approval && (
            <div className="bg-amber-50/90 rounded-2xl border-2 border-amber-400 shadow-md p-5 space-y-4 animate-in fade-in zoom-in-95 duration-200">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-bold text-amber-900 tracking-tight">
                    Human Approval Required
                  </h3>
                  <p className="text-xs text-amber-700 mt-0.5">
                    Deterministic policy paused execution. Review proposed tool call before dispatching to Policy Gateway.
                  </p>
                </div>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-amber-200/80 space-y-2.5 text-xs">
                <div className="flex justify-between items-center pb-2 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">Proposed Tool</span>
                  <span className="font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    {approval.tool}
                  </span>
                </div>

                <div className="flex justify-between items-center pb-2 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">Triggering Policy Rule</span>
                  <span className="font-mono font-semibold text-amber-800">
                    {approval.policy_rule || "REF-001"}
                  </span>
                </div>

                <div className="flex justify-between items-center pb-2 border-b border-slate-100">
                  <span className="text-slate-500 font-medium">Approver Role</span>
                  <span className="font-semibold text-slate-800 uppercase tracking-wide text-[10px]">
                    {approval.approver_role || "Support Lead"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 font-medium block mb-1">Arguments</span>
                  <pre className="p-2.5 bg-slate-900 text-emerald-400 rounded-lg font-mono text-[11px] overflow-x-auto">
                    {JSON.stringify(approval.args_full || approval.args_redacted || {}, null, 2)}
                  </pre>
                </div>

                {risk_flags.length > 0 && (
                  <div>
                    <span className="text-slate-500 font-medium block mb-1">Risk Flags</span>
                    <div className="flex flex-wrap gap-1">
                      {risk_flags.map((flag: string, i: number) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded bg-red-100 text-red-700 border border-red-200 font-mono text-[10px]"
                        >
                          {flag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 4 APPROVAL ACTION BUTTONS */}
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  onClick={handleApprove}
                  disabled={actionLoading}
                  id="approve-and-execute-btn"
                  className="px-3.5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-semibold text-xs shadow-xs flex items-center justify-center gap-1.5 transition-all"
                >
                  <Check className="w-4 h-4" />
                  <span>Approve & Execute</span>
                </button>

                <button
                  onClick={handleOpenEdit}
                  disabled={actionLoading}
                  className="px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 font-semibold text-xs shadow-xs flex items-center justify-center gap-1.5 transition-all"
                >
                  <Edit3 className="w-3.5 h-3.5 text-slate-600" />
                  <span>Edit</span>
                </button>

                <button
                  onClick={() => setRejectModalOpen(true)}
                  disabled={actionLoading}
                  className="px-3.5 py-2 rounded-xl bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 font-medium text-xs flex items-center justify-center gap-1.5 transition-all"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Reject</span>
                </button>

                <button
                  onClick={() => setEscalateModalOpen(true)}
                  disabled={actionLoading}
                  className="px-3.5 py-2 rounded-xl bg-orange-50 hover:bg-orange-100 border border-orange-200 text-orange-700 font-medium text-xs flex items-center justify-center gap-1.5 transition-all"
                >
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  <span>Escalate</span>
                </button>
              </div>
            </div>
          )}

          {/* SECTION 7: POLICY DECISION */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-900">Policy Decision Engine</h2>
            </div>

            {policy_decision ? (
              <div className="space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Tier Assessment</span>
                  <TierBadge tier={policy_decision.tier || "auto"} />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Rule Triggered</span>
                  <span className="font-mono font-bold text-slate-800">{policy_decision.rule_id}</span>
                </div>
                {policy_decision.reason && (
                  <p className="p-2.5 bg-slate-50 rounded-lg text-slate-700 text-[11px] border border-slate-100">
                    {policy_decision.reason}
                  </p>
                )}
              </div>
            ) : (
              <div className="text-xs text-slate-400 py-2">No policy decision evaluated yet.</div>
            )}
          </div>

          {/* SECTION 5: AI ANALYSIS (GROQ) */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
              <Cpu className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-900">AI Analysis & Planning</h2>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Classified Category</span>
                <span className="font-mono font-semibold text-slate-800 capitalize">{category}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Model Confidence</span>
                <span className="font-mono font-semibold text-slate-800">
                  {typeof confidence === "number" ? `${Math.round(confidence * 100)}%` : "n/a"}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Security Injection Scan</span>
                {risk_flags.includes("injection_suspected") || risk_flags.includes("prompt_injection_suspected") ? (
                  <span className="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-red-100 text-red-700 border border-red-200">
                    ADVERSARIAL SUSPECTED
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-emerald-100 text-emerald-800 border border-emerald-200">
                    PASSED / CLEAN
                  </span>
                )}
              </div>

              {ai_analysis.reasoning_summary && (
                <div className="pt-2">
                  <span className="text-slate-500 text-[11px] block mb-1">Reasoning Summary</span>
                  <p className="p-2.5 bg-slate-50 rounded-lg text-slate-700 text-[11px] border border-slate-100">
                    {ai_analysis.reasoning_summary}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* SECTION 2 & 3: CUSTOMER & IDENTITY VERIFICATION */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
              <Building className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-900">Customer & Identity Verification</h2>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Account Name</span>
                <span className="font-semibold text-slate-900">{customer?.name || "Unregistered / Unknown"}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-500">Identity Binding</span>
                {identity?.verified ? (
                  <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold text-[11px]">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Authorized Contact
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-amber-700 font-semibold text-[11px]">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Unverified / External
                  </span>
                )}
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-500">Account Plan</span>
                <span className="font-mono text-slate-800">{customer?.plan || "None"}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-500">Account Flags</span>
                <div className="flex gap-1">
                  {customer.is_strategic && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                      STRATEGIC
                    </span>
                  )}
                  {customer.is_legal_hold && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded font-semibold bg-red-50 text-red-700 border border-red-200">
                      LEGAL HOLD
                    </span>
                  )}
                  {!customer.is_strategic && !customer.is_legal_hold && (
                    <span className="text-slate-400 font-mono text-[11px]">Standard</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── SECTION 6, 8, 11, 12: LOWER ENTERPRISE DETAIL PANELS ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* SECTION 6: RETRIEVED KNOWLEDGE (HYBRID RAG) */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
            <Database className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-bold text-slate-900">Retrieved Policy Knowledge</h2>
          </div>

          <div className="space-y-2 text-xs">
            {retrieved_knowledge && retrieved_knowledge.length > 0 ? (
              retrieved_knowledge.map((citation: any, i: number) => {
                const score = citation.relevance_score !== undefined ? citation.relevance_score : citation.score;
                const title = citation.title || citation.document || citation.document_id || "Policy Document";
                const snippet = citation.content || citation.snippet || "Governing policy rules retrieved from Qdrant + BM25 hybrid index.";
                return (
                  <div key={i} className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1">
                    <div className="font-semibold text-blue-700 flex items-center justify-between">
                      <span className="truncate pr-2">
                        {title} {citation.section ? `§${citation.section}` : ""}
                      </span>
                      {score !== undefined && score !== null && (
                        <span className="font-mono text-[10px] text-slate-400 shrink-0">
                          Score: {Number(score).toFixed(2)}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-600 leading-normal line-clamp-3">
                      {snippet}
                    </p>
                  </div>
                );
              })
            ) : (
              <p className="text-slate-400 py-3 text-center">Hybrid policy citations indexed.</p>
            )}
          </div>
        </div>

        {/* SECTION 11: EXECUTION RESULT (POLICY GATEWAY DISPATCH) */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
            <Lock className="w-4 h-4 text-emerald-600" />
            <h2 className="text-sm font-bold text-slate-900">Policy Gateway Execution</h2>
          </div>

          {execution_result && execution_result.length > 0 ? (
            <div className="space-y-3 text-xs">
              {execution_result.map((ex: any, i: number) => {
                const isError = Boolean(
                  ex.result?.error || ex.error || (ex.result && ex.result.status === "failed")
                );
                return (
                  <div
                    key={i}
                    className={`p-3 border rounded-xl space-y-2 ${
                      isError
                        ? "bg-red-50/50 border-red-200"
                        : "bg-emerald-50/50 border-emerald-200"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`font-mono font-bold ${isError ? "text-red-800" : "text-emerald-800"}`}>
                        {ex.tool}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          isError
                            ? "bg-red-200/60 text-red-900"
                            : "bg-emerald-200/60 text-emerald-900"
                        }`}
                      >
                        {isError ? "FAILED" : "COMMITTED"}
                      </span>
                    </div>

                    <div className="font-mono text-[11px] text-slate-700 space-y-1">
                      <div>
                        Status:{" "}
                        <span className={isError ? "text-red-700 font-semibold" : "text-emerald-700 font-semibold"}>
                          {isError ? "FAILED" : "SUCCESS"}
                        </span>
                      </div>
                      {ex.audit_event_id && <div>Audit Event: {ex.audit_event_id}</div>}
                      {ex.idempotent_replay && <div className="text-blue-600">Replay: Idempotent</div>}
                    </div>

                    {ex.result && (
                      <pre
                        className={`p-2 rounded-lg text-[10px] font-mono overflow-x-auto ${
                          isError
                            ? "bg-slate-900 text-red-400"
                            : "bg-slate-900 text-emerald-400"
                        }`}
                      >
                        {JSON.stringify(ex.result, null, 2)}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-slate-400 text-xs py-4 text-center">
              {status === "awaiting_approval"
                ? "Awaiting human review before gateway execution"
                : "No write tool executions triggered"}
            </div>
          )}
        </div>

        {/* SECTION 12: AUDIT TIMELINE */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
            <Hash className="w-4 h-4 text-purple-600" />
            <h2 className="text-sm font-bold text-slate-900">Audit & Governance Log</h2>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="p-2.5 rounded-lg border border-slate-100 bg-slate-50 space-y-1">
              <div className="flex justify-between font-semibold text-slate-800 text-[11px]">
                <span>ticket_ingested</span>
                <span className="font-mono text-[10px] text-slate-400">{timeAgo(created_at)}</span>
              </div>
              <p className="text-[10px] font-mono text-slate-500">actor: system • id: {ticketId.slice(0, 8)}</p>
            </div>

            {isAwaitingApproval && (
              <div className="p-2.5 rounded-lg border border-amber-200 bg-amber-50/50 space-y-1">
                <div className="flex justify-between font-semibold text-amber-900 text-[11px]">
                  <span>approval_paused</span>
                  <span className="font-mono text-[10px] text-amber-600">pending</span>
                </div>
                <p className="text-[10px] font-mono text-amber-700">
                  rule: {policy_decision?.rule_id || "REF-001"} • tier: approval
                </p>
              </div>
            )}

            {execution_result && execution_result.length > 0 && (
              <div className="p-2.5 rounded-lg border border-emerald-200 bg-emerald-50/50 space-y-1">
                <div className="flex justify-between font-semibold text-emerald-900 text-[11px]">
                  <span>gateway_executed</span>
                  <span className="font-mono text-[10px] text-emerald-700">verified</span>
                </div>
                <p className="text-[10px] font-mono text-emerald-700">
                  event_id: {execution_result[0]?.audit_event_id || "gw-exec"} • read-back: confirmed
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── EDIT ARGUMENTS MODAL ── */}
      {editModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-5 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <h3 className="font-bold text-sm text-slate-900">Edit Proposed Tool Arguments</h3>
              <button onClick={() => setEditModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Modify arguments before execution. Gateway will re-hash and enforce policy limits.
            </p>
            <textarea
              rows={8}
              value={editArgsJson}
              onChange={(e) => setEditArgsJson(e.target.value)}
              className="w-full p-3 font-mono text-xs rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:border-blue-500"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setEditModalOpen(false)}
                className="px-3.5 py-1.5 text-xs rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmEdit}
                disabled={actionLoading}
                className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white"
              >
                Save & Execute
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── REJECT MODAL ── */}
      {rejectModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-5 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <h3 className="font-bold text-sm text-slate-900">Reject Proposed Action</h3>
              <button onClick={() => setRejectModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-500">
              The action will not be dispatched. Ticket will be marked blocked with reason recorded in audit log.
            </p>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Enter rejection rationale..."
              className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-red-500"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setRejectModalOpen(false)}
                className="px-3.5 py-1.5 text-xs rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReject}
                disabled={actionLoading}
                className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-red-600 hover:bg-red-700 text-white"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── ESCALATE MODAL ── */}
      {escalateModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-5 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <h3 className="font-bold text-sm text-slate-900">Escalate Action to Senior Management</h3>
              <button onClick={() => setEscalateModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Transfers approval authority to VP Support / Legal Hold committee.
            </p>
            <textarea
              rows={3}
              value={escalateReason}
              onChange={(e) => setEscalateReason(e.target.value)}
              placeholder="Reason for escalation..."
              className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setEscalateModalOpen(false)}
                className="px-3.5 py-1.5 text-xs rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmEscalate}
                disabled={actionLoading}
                className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-orange-600 hover:bg-orange-700 text-white"
              >
                Confirm Escalation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
