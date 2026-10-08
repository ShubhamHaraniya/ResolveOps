"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  ExternalLink,
  ShieldAlert,
  Hash,
  Eye,
  Check,
  X,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { formatCurrency, timeAgo } from "@/lib/utils";
import { ApprovalItem } from "@/lib/types";

export default function ApprovalsPage() {
  const { approvals, approveAction, rejectAction, killSwitch } = useApp();
  const [activeTab, setActiveTab] = useState<string>("All");
  const [selectedApproval, setSelectedApproval] = useState<ApprovalItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectInput, setShowRejectInput] = useState(false);

  const tabs = ["All", "Financial", "Security", "Low Confidence", "Conflicts"];

  const filteredApprovals = approvals.filter((item) => {
    if (activeTab === "All") return true;
    return item.category === activeTab;
  });

  const handleOpenModal = (item: ApprovalItem) => {
    setSelectedApproval(item);
    setShowRejectInput(false);
    setRejectReason("");
    setModalOpen(true);
  };

  const handleApprove = (id: string) => {
    if (killSwitch) {
      alert("GLOBAL KILL SWITCH ACTIVE: Action execution rejected by policy gateway.");
      return;
    }
    approveAction(id);
    if (modalOpen) setModalOpen(false);
  };

  const handleReject = (id: string) => {
    rejectAction(id, rejectReason || "Rejected in approval queue");
    setModalOpen(false);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Human-In-The-Loop Approval Queue
            </h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-50 text-amber-700 border border-amber-200">
              {approvals.length} PENDING
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Cryptographically hash-bound side-effect authorizations requiring explicit human sign-off
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200 pb-px">
        {tabs.map((tab) => {
          const count =
            tab === "All"
              ? approvals.length
              : approvals.filter((a) => a.category === tab).length;

          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-xs font-medium border-b-2 -mb-px flex items-center gap-2 transition-all ${
                activeTab === tab
                  ? "border-blue-600 text-blue-600 font-semibold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <span>{tab}</span>
              {count > 0 && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    activeTab === tab
                      ? "bg-blue-100 text-blue-700 font-bold"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Approvals Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {filteredApprovals.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="font-semibold text-slate-800">All caught up!</p>
            <p className="text-slate-400 mt-0.5">No pending approval requests in this category.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                  <th className="py-3 px-4">Ticket</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4">Action Summary</th>
                  <th className="py-3 px-4">Amount</th>
                  <th className="py-3 px-4">Risk Tier</th>
                  <th className="py-3 px-4">Policy Rule</th>
                  <th className="py-3 px-4">Approver Role</th>
                  <th className="py-3 px-4">Expires In</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredApprovals.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-semibold text-blue-600">
                      <Link href={`/tickets/${item.ticket_id}`} className="hover:underline">
                        {item.ticket_number}
                      </Link>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-900">
                      {item.customer_name}
                    </td>
                    <td className="py-3.5 px-4 text-slate-700 max-w-sm font-medium">
                      {item.action_summary}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                      {item.amount !== undefined ? formatCurrency(item.amount) : "—"}
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          item.risk_badge === "High" || item.risk_badge === "Critical"
                            ? "bg-red-50 text-red-700 border border-red-200"
                            : item.risk_badge === "Medium"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : "bg-blue-50 text-blue-700 border border-blue-200"
                        }`}
                      >
                        {item.risk_badge} Risk
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-600 font-medium">
                      {item.policy_rule}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 text-[11px]">
                      {item.approver_role}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-amber-700">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-amber-500" />
                        23h 44m
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenModal(item)}
                          className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                          title="Inspect Details"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleApprove(item.id)}
                          className="px-2 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium text-[11px] flex items-center gap-1 shadow-xs"
                        >
                          <Check className="w-3 h-3" />
                          Approve
                        </button>
                        <button
                          onClick={() => {
                            setSelectedApproval(item);
                            setShowRejectInput(true);
                            setModalOpen(true);
                          }}
                          className="p-1 rounded hover:bg-red-50 text-red-600 border border-transparent hover:border-red-200"
                          title="Reject"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal */}
      {modalOpen && selectedApproval && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-xl w-full p-6 animate-in fade-in zoom-in-95 duration-150 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700">
                  {selectedApproval.ticket_number}
                </span>
                <h3 className="text-sm font-bold text-slate-900 mt-1">
                  Authorize Side-Effect Dispatch
                </h3>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Summary
                </label>
                <p className="font-medium text-slate-800 mt-0.5">{selectedApproval.action_summary}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
                <div>
                  <span className="text-slate-400">Target Tool:</span>
                  <div className="font-mono font-semibold text-slate-900">{selectedApproval.tool}</div>
                </div>
                <div>
                  <span className="text-slate-400">Policy Mandate:</span>
                  <div className="font-mono font-semibold text-slate-900">{selectedApproval.policy_rule}</div>
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                  <Hash className="w-3.5 h-3.5" />
                  Cryptographic Parameters & Hash
                </label>
                <pre className="mt-1 p-2.5 rounded bg-slate-900 text-slate-100 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedApproval.args, null, 2)}
                </pre>
                <div className="mt-1 text-[10px] font-mono text-slate-400 truncate">
                  SHA256: {selectedApproval.args_hash}
                </div>
              </div>

              {showRejectInput && (
                <div className="pt-2 border-t border-slate-100">
                  <label className="text-xs font-semibold text-red-700">Rejection Justification</label>
                  <textarea
                    rows={2}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Enter reason for rejection..."
                    className="mt-1 w-full p-2 text-xs rounded border border-red-300 focus:outline-none focus:border-red-500"
                  />
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
              <Link
                href={`/tickets/${selectedApproval.ticket_id}`}
                className="text-xs text-blue-600 hover:underline flex items-center gap-1"
              >
                Go to Ticket Workspace &rarr;
              </Link>

              <div className="flex items-center gap-2">
                {showRejectInput ? (
                  <button
                    onClick={() => handleReject(selectedApproval.id)}
                    className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium text-xs shadow-xs"
                  >
                    Confirm Reject
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => setShowRejectInput(true)}
                      className="px-3 py-2 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 text-xs font-medium"
                    >
                      Reject
                    </button>
                    <button
                      onClick={() => handleApprove(selectedApproval.id)}
                      className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs shadow-xs"
                    >
                      Approve & Execute
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
