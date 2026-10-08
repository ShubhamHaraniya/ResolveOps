"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  History,
  ShieldCheck,
  ShieldAlert,
  Download,
  Filter,
  Search,
  CheckCircle2,
  Lock,
  ExternalLink,
  Hash,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { formatDate, timeAgo } from "@/lib/utils";

export default function AuditLogPage() {
  const { auditLog } = useApp();
  const [filterEvent, setFilterEvent] = useState<string>("all");
  const [filterActor, setFilterActor] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredEvents = auditLog.filter((ev) => {
    const matchesEvent = filterEvent === "all" || ev.event === filterEvent;
    const matchesActor = filterActor === "all" || ev.actor_type === filterActor;
    const matchesSearch =
      ev.ticket_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ev.event.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (ev.tool && ev.tool.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (ev.policy_rule && ev.policy_rule.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesEvent && matchesActor && matchesSearch;
  });

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(auditLog, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resolveops-audit-${new Date().toISOString().split("T")[0]}.json`;
    a.click();
  };

  const exportCSV = () => {
    const headers = "id,timestamp,ticket_id,actor_type,event,tool,policy_rule,result_status,row_hash\n";
    const rows = auditLog
      .map(
        (e) =>
          `"${e.id}","${e.timestamp}","${e.ticket_id}","${e.actor_type}","${e.event}","${e.tool || ""}","${e.policy_rule || ""}","${e.result_status}","${e.row_hash}"`
      )
      .join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resolveops-audit-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Tamper-Evident Audit Ledger
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1.5">
              <Lock className="w-3 h-3 text-emerald-600" />
              Cryptographic Hash Chain Intact
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable append-only record with PII redaction and SHA-256 state linking
          </p>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={exportJSON}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-xs"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export JSON</span>
          </button>
          <button
            onClick={exportCSV}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-xs"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by ticket, tool, policy, event..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <select
            value={filterActor}
            onChange={(e) => setFilterActor(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none"
          >
            <option value="all">All Actors</option>
            <option value="agent">Agent (Groq/LangGraph)</option>
            <option value="gateway">Policy Gateway</option>
            <option value="human">Human Reviewer</option>
            <option value="system">System / Webhook</option>
          </select>

          <select
            value={filterEvent}
            onChange={(e) => setFilterEvent(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none"
          >
            <option value="all">All Events</option>
            <option value="ticket_ingested">ticket_ingested</option>
            <option value="identity_verified">identity_verified</option>
            <option value="context_gathered">context_gathered</option>
            <option value="policy_evaluated">policy_evaluated</option>
            <option value="approval_requested">approval_requested</option>
            <option value="action_executed">action_executed</option>
            <option value="gateway_blocked">gateway_blocked</option>
          </select>
        </div>
      </div>

      {/* Audit Events Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Ticket</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Event</th>
                <th className="py-3 px-4">Target Tool / Policy</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Redacted Payload</th>
                <th className="py-3 px-4 text-right">Row Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {filteredEvents.map((ev) => (
                <tr key={ev.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                    {formatDate(ev.timestamp)}
                  </td>
                  <td className="py-3 px-4 font-semibold text-blue-600">
                    <Link href={`/tickets/${ev.ticket_id}`} className="hover:underline">
                      {ev.ticket_id}
                    </Link>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-700 uppercase">
                      {ev.actor_type}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-900">
                    {ev.event}
                  </td>
                  <td className="py-3 px-4 text-slate-700">
                    {ev.tool && <span className="text-blue-600 mr-2">{ev.tool}</span>}
                    {ev.policy_rule && (
                      <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 text-[10px]">
                        {ev.policy_rule}
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        ev.result_status === "SUCCESS"
                          ? "bg-emerald-50 text-emerald-700"
                          : ev.result_status === "BLOCKED"
                          ? "bg-red-50 text-red-700"
                          : ev.result_status === "INTERRUPTED"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {ev.result_status}
                    </span>
                  </td>
                  <td className="py-3 px-4 max-w-xs truncate text-slate-600" title={JSON.stringify(ev.args_redacted)}>
                    {ev.args_redacted ? JSON.stringify(ev.args_redacted) : "—"}
                  </td>
                  <td
                    className="py-3 px-4 text-right text-slate-400 truncate max-w-[120px]"
                    title={`Row: ${ev.row_hash}\nPrev: ${ev.prev_hash}`}
                  >
                    {ev.row_hash.substring(0, 10)}...
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
