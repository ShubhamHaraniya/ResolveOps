"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Eye,
  Check,
  X,
  RotateCw,
} from "lucide-react";
import { timeAgo } from "@/lib/utils";
import { approveTicketAction, rejectTicketAction } from "@/lib/api";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("All");
  const [selectedApproval, setSelectedApproval] = useState<any | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const tabs = ["All", "Billing", "Access"];

  const loadApprovals = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/approvals?status=pending", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setApprovals(data.approvals || []);
      }
    } catch (err) {
      console.warn("Failed to fetch approvals:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const filteredApprovals = approvals.filter((item) => {
    if (activeTab === "All") return true;
    if (activeTab === "Billing") return item.tool?.startsWith("billing");
    if (activeTab === "Access") return item.tool?.startsWith("access");
    return true;
  });

  const handleOpenModal = (item: any) => {
    setSelectedApproval(item);
    setShowRejectInput(false);
    setRejectReason("");
    setModalOpen(true);
  };

  const handleApprove = async (id: string) => {
    setActionLoading(true);
    try {
      await approveTicketAction(id, "support_lead_01", "Approved via Approval Queue");
      setModalOpen(false);
      await loadApprovals();
    } catch (err: any) {
      alert("Approval error: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id: string) => {
    setActionLoading(true);
    try {
      await rejectTicketAction(id, rejectReason || "Rejected in approval queue");
      setModalOpen(false);
      await loadApprovals();
    } catch (err: any) {
      alert("Rejection error: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Approval Queue
            </h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-50 text-amber-700 border border-amber-200">
              {approvals.length} PENDING
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Pending tool calls that policy requires a human to approve before they run
          </p>
        </div>

        <button
          onClick={loadApprovals}
          className="p-2 text-xs rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-blue-600" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200 pb-px">
        {tabs.map((tab) => {
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
                  <th className="py-3 px-4">Subject</th>
                  <th className="py-3 px-4">Proposed Tool</th>
                  <th className="py-3 px-4">Arguments</th>
                  <th className="py-3 px-4">Policy Rule</th>
                  <th className="py-3 px-4">Age</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredApprovals.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-blue-600">
                      <Link href={`/tickets/${item.ticket_id}`} className="hover:underline">
                        {item.ticket_number}
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-slate-800 font-medium max-w-xs truncate">
                      {item.subject}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700">
                      <span className="bg-slate-100 px-1.5 py-0.5 rounded text-[11px] font-medium border border-slate-200">
                        {item.tool}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-600 font-mono text-[11px] max-w-xs truncate">
                      {JSON.stringify(item.args)}
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-amber-700">
                      {item.policy_rule}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                      {timeAgo(item.created_at)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenModal(item)}
                          className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleApprove(item.id)}
                          disabled={actionLoading}
                          className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-[11px] flex items-center gap-1"
                        >
                          <Check className="w-3 h-3" /> Approve
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

      {/* DETAIL MODAL */}
      {modalOpen && selectedApproval && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <h3 className="font-bold text-sm text-slate-900">Review Approval Request</h3>
              <button onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Ticket</span>
                <span className="font-mono font-semibold text-blue-600">{selectedApproval.ticket_number}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Tool</span>
                <span className="font-mono font-semibold text-slate-900">{selectedApproval.tool}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Policy Rule</span>
                <span className="font-mono text-amber-700 font-bold">{selectedApproval.policy_rule}</span>
              </div>
              <div>
                <span className="text-slate-500 block mb-1">Arguments</span>
                <pre className="p-3 bg-slate-900 text-emerald-400 rounded-lg font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedApproval.args, null, 2)}
                </pre>
              </div>

              {showRejectInput && (
                <div className="pt-2">
                  <textarea
                    rows={2}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Enter reason for rejection..."
                    className="w-full p-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-between pt-3 border-t border-slate-100">
              <button
                onClick={() => {
                  if (!showRejectInput) setShowRejectInput(true);
                  else handleReject(selectedApproval.id);
                }}
                disabled={actionLoading}
                className="px-3.5 py-1.5 text-xs rounded-lg bg-red-50 text-red-700 hover:bg-red-100 font-medium"
              >
                {showRejectInput ? "Confirm Reject" : "Reject"}
              </button>

              <div className="flex gap-2">
                <button
                  onClick={() => setModalOpen(false)}
                  className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleApprove(selectedApproval.id)}
                  disabled={actionLoading}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  Approve & Execute
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
