"use client";

import React, { useState, Suspense } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  FileText,
  ChevronDown,
  ChevronUp,
  Hash,
  User,
  Bot,
  Building,
  Key,
  CreditCard,
  GitFork,
  Edit3,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { TierBadge, PriorityBadge, StatusBadge } from "@/components/Badges";
import { formatCurrency, formatDate, timeAgo } from "@/lib/utils";

function TicketDetailContent() {
  const params = useParams();
  const ticketId = (params?.id as string) || "tick-101";
  const { getTicketById, approvals, approveAction, rejectAction, killSwitch } = useApp();

  const ticket = getTicketById(ticketId) || getTicketById("tick-101");

  const [apiEffectExpanded, setApiEffectExpanded] = useState(true);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editedAmount, setEditedAmount] = useState<string>("30.00");
  const [isExecuting, setIsExecuting] = useState(false);

  if (!ticket) {
    return (
      <div className="p-8 text-center text-xs text-slate-500">
        Ticket not found. <Link href="/tickets" className="text-blue-600 underline">Return to Tickets</Link>
      </div>
    );
  }

  const matchingApproval = approvals.find((a) => a.ticket_id === ticket.id);

  const handleApprove = () => {
    if (!matchingApproval) return;
    setIsExecuting(true);
    setTimeout(() => {
      approveAction(matchingApproval.id);
      setIsExecuting(false);
    }, 600);
  };

  const handleReject = () => {
    if (!matchingApproval) return;
    rejectAction(matchingApproval.id, rejectReason || "Rejected by Support Lead review");
    setRejectModalOpen(false);
  };

  const handleSaveEdit = () => {
    if (!matchingApproval) return;
    approveAction(matchingApproval.id, {
      ...matchingApproval.args,
      amount: parseFloat(editedAmount) || matchingApproval.args.amount,
    });
    setEditModalOpen(false);
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-5">
      {/* Back and Breadcrumbs */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <Link
            href="/tickets"
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-base font-bold text-slate-900">
                {ticket.ticket_number}
              </span>
              <TierBadge tier={ticket.tier} />
              <PriorityBadge priority={ticket.priority} />
              <StatusBadge status={ticket.status} />
            </div>
            <h2 className="text-xs text-slate-600 font-medium mt-0.5">
              {ticket.subject}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <Link
            href={`/traces/${ticket.run_id || "run-9801-refund"}`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium"
          >
            <GitFork className="w-3.5 h-3.5 text-blue-600" />
            <span>LangGraph Trace</span>
          </Link>
          <span className="text-slate-400 font-mono text-[11px]">
            Created {timeAgo(ticket.created_at)}
          </span>
        </div>
      </div>

      {/* 3-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* ================= LEFT COLUMN (Col 1-3) ================= */}
        <div className="lg:col-span-3 space-y-4">
          {/* Customer Profile Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-slate-400" />
                Customer Account
              </span>
              <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-100 text-slate-700 font-semibold">
                {ticket.customer.plan}
              </span>
            </div>

            <div>
              <div className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                {ticket.customer.name}
              </div>
              <div className="text-xs text-slate-500">{ticket.customer.domain}</div>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {ticket.customer.is_strategic && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                  STRATEGIC ACCOUNT
                </span>
              )}
              {ticket.customer.is_legal_hold && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-50 text-red-700 border border-red-200">
                  LEGAL HOLD ACTIVE
                </span>
              )}
            </div>

            <div className="pt-2 border-t border-slate-100 space-y-1.5 text-xs text-slate-600">
              <div className="flex justify-between">
                <span className="text-slate-400">ARR</span>
                <span className="font-semibold text-slate-900 font-mono">
                  {formatCurrency(ticket.customer.arr)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Account Owner</span>
                <span>{ticket.customer.owner}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">CSM</span>
                <span>{ticket.customer.csm}</span>
              </div>
            </div>
          </div>

          {/* Identity Provenance Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-2.5">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-slate-400" />
              Identity Verification
            </span>

            {ticket.customer.verified_contact?.is_verified ? (
              <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800">
                <div className="flex items-center gap-1.5 text-xs font-semibold">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Requester Verified (99%)</span>
                </div>
                <div className="mt-1 text-[11px] text-emerald-700 font-mono">
                  {ticket.requester_email}
                </div>
                <div className="mt-1 text-[10px] text-emerald-600">
                  Method: {ticket.customer.verified_contact.verification_method}
                </div>
              </div>
            ) : (
              <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-800">
                <div className="flex items-center gap-1.5 text-xs font-semibold">
                  <ShieldAlert className="w-4 h-4 text-red-600" />
                  <span>Identity Mismatch / Unverified</span>
                </div>
                <div className="mt-1 text-[11px] text-red-700 font-mono">
                  {ticket.requester_email}
                </div>
                <div className="mt-1 text-[10px] text-red-600">
                  Provenance check failed at Gateway Step 4.
                </div>
              </div>
            )}
          </div>

          {/* Invoices List */}
          {ticket.invoices && ticket.invoices.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-2.5">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                <CreditCard className="w-3.5 h-3.5 text-slate-400" />
                Related Billing Invoices
              </span>
              <div className="divide-y divide-slate-100 text-xs">
                {ticket.invoices.map((inv) => (
                  <div key={inv.id} className="py-2 flex items-center justify-between">
                    <div>
                      <div className="font-mono font-medium text-slate-800">
                        {inv.number}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {formatDate(inv.issued_at)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono font-bold text-slate-900">
                        {formatCurrency(inv.amount)}
                      </div>
                      <span className="text-[10px] px-1.5 py-0.2 rounded font-mono bg-emerald-50 text-emerald-700">
                        {inv.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ================= CENTER COLUMN (Col 4-8) ================= */}
        <div className="lg:col-span-5 space-y-4">
          {/* Conversation Thread */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-800">
                Ticket Conversation & Execution Transcript
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                {ticket.messages.length} events
              </span>
            </div>

            <div className="p-4 space-y-4 max-h-[500px] overflow-y-auto">
              {ticket.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`p-3.5 rounded-xl border text-xs leading-relaxed ${
                    msg.sender_type === "system"
                      ? "bg-slate-50 border-slate-200 text-slate-700"
                      : msg.sender_type === "agent"
                      ? "bg-indigo-50/60 border-indigo-200 text-indigo-950"
                      : "bg-blue-50/50 border-blue-200 text-blue-950"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 font-semibold">
                      {msg.sender_type === "system" ? (
                        <ShieldCheck className="w-3.5 h-3.5 text-slate-600" />
                      ) : msg.sender_type === "agent" ? (
                        <Bot className="w-3.5 h-3.5 text-indigo-600" />
                      ) : (
                        <User className="w-3.5 h-3.5 text-blue-600" />
                      )}
                      <span>{msg.sender_name}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {timeAgo(msg.timestamp)}
                    </span>
                  </div>
                  <div className="whitespace-pre-wrap">{msg.body}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Evidence Gathered Panel */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              Verified Evidence & Grounding Data
            </span>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">
                  CRM Match
                </span>
                <p className="font-medium text-slate-800">
                  {ticket.customer.name} (Plan: {ticket.customer.plan})
                </p>
                <p className="text-[11px] text-slate-500">
                  Status: Active · ARR: {formatCurrency(ticket.customer.arr)}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">
                  Billing Ledger
                </span>
                <p className="font-medium text-slate-800">
                  Invoice #INV-2026-881 Verified
                </p>
                <p className="text-[11px] text-slate-500">
                  Amount: $30.00 · Stripe ID: ch_9102834190
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ================= RIGHT COLUMN (Col 9-12) ================= */}
        <div className="lg:col-span-4 space-y-4">
          {/* AI Analysis Summary */}
          {ticket.ai_analysis && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  AI Model Classification
                </span>
                <span className="font-mono text-xs font-bold text-blue-600">
                  {Math.round(ticket.ai_analysis.confidence * 100)}% Conf
                </span>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed">
                {ticket.ai_analysis.summary}
              </p>
            </div>
          )}

          {/* Risk Flags */}
          {ticket.risk_flags.length > 0 && (
            <div className="bg-white rounded-xl border border-amber-200 p-4 shadow-xs bg-amber-50/20 space-y-2">
              <span className="text-[11px] font-semibold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                Active Risk Flags ({ticket.risk_flags.length})
              </span>
              <div className="space-y-1">
                {ticket.risk_flags.map((flag, i) => (
                  <div
                    key={i}
                    className="text-xs font-mono px-2 py-1 rounded bg-amber-100/60 text-amber-900 border border-amber-200/80"
                  >
                    &bull; {flag}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* RAG Citations */}
          {ticket.rag_citations && ticket.rag_citations.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-2">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Grounding Policy Citation
              </span>
              {ticket.rag_citations.map((cite) => (
                <div key={cite.id} className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                  <div className="flex items-center justify-between font-semibold text-slate-800">
                    <span>{cite.title}</span>
                    <span className="text-[10px] font-mono text-blue-600">{cite.version}</span>
                  </div>
                  <div className="text-[11px] font-medium text-slate-600">{cite.section}</div>
                  <p className="text-[11px] text-slate-500 italic mt-1">&ldquo;{cite.snippet}&rdquo;</p>
                  <Link
                    href="/knowledge-base"
                    className="text-[11px] text-blue-600 hover:underline flex items-center gap-1 pt-1 font-medium"
                  >
                    Open in Knowledge Base &rarr;
                  </Link>
                </div>
              ))}
            </div>
          )}

          {/* PROPOSED ACTION & GATEWAY DISPATCH CARD */}
          {ticket.proposed_action && (
            <div
              className={`rounded-xl border p-4 shadow-xs space-y-3.5 ${
                ticket.proposed_action.status === "executed"
                  ? "bg-emerald-50/50 border-emerald-300"
                  : ticket.proposed_action.tier === "forbidden"
                  ? "bg-red-50/40 border-red-300"
                  : "bg-white border-blue-200 ring-1 ring-blue-500/10"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-700">
                  {ticket.proposed_action.status === "executed"
                    ? "Action Executed & Verified"
                    : ticket.proposed_action.tier === "forbidden"
                    ? "Action Forbidden"
                    : "Proposed Side-Effect"}
                </span>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded font-bold bg-slate-100 text-slate-700">
                  {ticket.proposed_action.policy_rule}
                </span>
              </div>

              <div>
                <div className="text-xs font-bold text-slate-900 font-mono">
                  {ticket.proposed_action.tool}
                </div>
                <div className="text-xs text-slate-600 mt-0.5">
                  {ticket.proposed_action.policy_rule_name}
                </div>
              </div>

              {/* Expandable API Effect */}
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-2.5 text-xs">
                <button
                  onClick={() => setApiEffectExpanded(!apiEffectExpanded)}
                  className="w-full flex items-center justify-between text-slate-600 font-medium text-[11px]"
                >
                  <span className="flex items-center gap-1">
                    <Hash className="w-3 h-3 text-slate-400" />
                    Exact API Payload & Hash
                  </span>
                  {apiEffectExpanded ? (
                    <ChevronUp className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </button>

                {apiEffectExpanded && (
                  <div className="mt-2 pt-2 border-t border-slate-200 space-y-2">
                    <pre className="text-[10px] font-mono text-slate-800 bg-white p-2 rounded border border-slate-200 overflow-x-auto">
                      {JSON.stringify(ticket.proposed_action.arguments, null, 2)}
                    </pre>
                    <div className="text-[10px] font-mono text-slate-500 truncate" title={ticket.proposed_action.args_hash}>
                      SHA-256: {ticket.proposed_action.args_hash.substring(0, 24)}...
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              {ticket.proposed_action.status === "pending_review" && matchingApproval && (
                <div className="space-y-2 pt-1">
                  <button
                    onClick={handleApprove}
                    disabled={isExecuting || killSwitch}
                    className="w-full py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs shadow-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>
                      {isExecuting
                        ? "Validating Gateway Hash..."
                        : "Approve & Execute via Gateway"}
                    </span>
                  </button>

                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={() => setEditModalOpen(true)}
                      className="py-1.5 px-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium flex items-center justify-center gap-1"
                    >
                      <Edit3 className="w-3 h-3" />
                      <span>Edit</span>
                    </button>
                    <button
                      onClick={() => setRejectModalOpen(true)}
                      className="py-1.5 px-2 rounded-lg border border-red-200 bg-white hover:bg-red-50 text-red-600 text-xs font-medium flex items-center justify-center gap-1"
                    >
                      <XCircle className="w-3 h-3" />
                      <span>Reject</span>
                    </button>
                    <button
                      onClick={() => alert("Ticket escalated to Head of Customer Operations.")}
                      className="py-1.5 px-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium flex items-center justify-center gap-1"
                    >
                      <span>Escalate</span>
                    </button>
                  </div>
                </div>
              )}

              {ticket.proposed_action.status === "executed" && (
                <div className="p-2.5 rounded-lg bg-emerald-100/60 border border-emerald-300 text-emerald-900 text-xs font-medium flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Execution Confirmed · 0 Duplicate Risk</span>
                </div>
              )}

              {ticket.proposed_action.tier === "forbidden" && (
                <div className="p-2.5 rounded-lg bg-red-100/60 border border-red-300 text-red-900 text-xs font-medium flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-red-600 shrink-0" />
                  <span>Execution Blocked by Gateway Policy</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Reject Modal */}
      {rejectModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <h3 className="text-base font-semibold text-slate-900">
              Reject Proposed Action
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              State the reason for rejecting this automated proposal. The feedback will be logged for model evaluation.
            </p>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g., Charge was already credited in prior billing cycle."
              className="mt-3 w-full p-2.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:border-red-500"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setRejectModalOpen(false)}
                className="px-3 py-1.5 rounded-md text-xs font-medium text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                className="px-3 py-1.5 rounded-md text-xs font-medium bg-red-600 text-white hover:bg-red-700"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <h3 className="text-base font-semibold text-slate-900">
              Edit Side-Effect Parameters
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              Modifying parameters triggers fresh policy evaluation and regenerates the cryptographic execution hash.
            </p>
            <div className="mt-4 space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-700">Refund Amount ($)</label>
                <input
                  type="number"
                  value={editedAmount}
                  onChange={(e) => setEditedAmount(e.target.value)}
                  className="mt-1 w-full p-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setEditModalOpen(false)}
                className="px-3 py-1.5 rounded-md text-xs font-medium text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600 text-white hover:bg-blue-700"
              >
                Revalidate & Approve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function TicketDetailPage() {
  return (
    <Suspense fallback={<div className="p-8 text-xs text-slate-400">Loading ticket details...</div>}>
      <TicketDetailContent />
    </Suspense>
  );
}
