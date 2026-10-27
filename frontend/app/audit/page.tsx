"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Download, Search, Lock, RotateCw, ShieldAlert, ShieldCheck } from "lucide-react";
import { timeAgo } from "@/lib/utils";
import { ErrorState } from "@/components/States";

interface ChainStatus {
  valid: boolean;
  total_events: number;
  verified_events: number;
  head_hash: string | null;
  error: string | null;
  checked_at: string;
}

const EVENT_OPTIONS = [
  "received", "proposed", "policy_decision", "approval_requested", "approved", "edited",
  "rejected", "executed", "verified", "failed", "escalated",
  "tool_call_start", "tool_call_result", "tool_call_denied",
];

function resultClass(status: string | null | undefined): string {
  const v = (status ?? "").toLowerCase();
  if (!v) return "bg-slate-50 text-slate-500 border border-slate-200";
  if (v.includes("denied") || v.includes("fail") || v.includes("error") || v.includes("block") || v.includes("reject")) {
    return "bg-red-50 text-red-700 border border-red-200";
  }
  return "bg-emerald-50 text-emerald-700 border border-emerald-200";
}

export default function AuditLogPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterEvent, setFilterEvent] = useState<string>("all");
  const [filterActor, setFilterActor] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [chain, setChain] = useState<ChainStatus | null>(null);
  const [verifying, setVerifying] = useState(false);

  const loadAuditLog = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams({ page_size: "200" });
      if (filterEvent !== "all") qs.set("event", filterEvent);
      if (filterActor !== "all") qs.set("actor", filterActor);
      const res = await fetch(`/api/audit?${qs}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setEvents(data.events ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      setEvents([]);
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [filterEvent, filterActor]);

  const verifyChain = useCallback(async () => {
    setVerifying(true);
    try {
      const res = await fetch("/api/audit/verify", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setChain(await res.json());
    } catch (err) {
      setChain({
        valid: false, total_events: 0, verified_events: 0, head_hash: null,
        error: err instanceof Error ? err.message : "Verification request failed",
        checked_at: new Date().toISOString(),
      });
    } finally {
      setVerifying(false);
    }
  }, []);

  useEffect(() => {
    loadAuditLog();
  }, [loadAuditLog]);

  const filteredEvents = events.filter((ev) => {
    const s = searchQuery.toLowerCase();
    return (
      !s ||
      (ev.ticket_id || "").toLowerCase().includes(s) ||
      (ev.event || "").toLowerCase().includes(s) ||
      (ev.tool && ev.tool.toLowerCase().includes(s)) ||
      (ev.policy_rule && ev.policy_rule.toLowerCase().includes(s))
    );
  });

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(events, null, 2)], {
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
    const rows = events
      .map(
        (e) =>
          `"${e.id}","${e.timestamp}","${e.ticket_id}","${e.actor_type}","${e.event}","${e.tool || ""}","${e.policy_rule || ""}","${e.result_status ?? ""}","${e.row_hash ?? ""}"`
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
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Audit Log</h1>
            {chain && (
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-mono font-bold border flex items-center gap-1 ${
                  chain.valid
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : "bg-red-50 text-red-700 border-red-200"
                }`}
              >
                {chain.valid ? <Lock className="w-3 h-3" /> : <ShieldAlert className="w-3 h-3" />}
                {chain.valid ? "HASH CHAIN VERIFIED" : "HASH CHAIN BROKEN"}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Append-only, hash-chained log of gateway tool calls, approvals and workflow decisions
            ({total} event{total === 1 ? "" : "s"} match the filters; showing the newest {events.length})
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadAuditLog}
            className="p-2 text-xs rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-blue-600" : ""}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={verifyChain}
            disabled={verifying}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer disabled:opacity-60"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{verifying ? "Verifying..." : "Verify chain"}</span>
          </button>

          <button
            onClick={exportCSV}
            className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" /> CSV
          </button>
          <button
            onClick={exportJSON}
            className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" /> JSON
          </button>
        </div>
      </div>

      {chain && (
        <div
          className={`px-4 py-3 rounded-lg border text-xs ${
            chain.valid ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-red-50 border-red-200 text-red-900"
          }`}
        >
          {chain.valid
            ? `Verified ${chain.verified_events} of ${chain.total_events} events from the genesis hash. Head: ${chain.head_hash ?? "n/a"}.`
            : `Verification failed after ${chain.verified_events} of ${chain.total_events} events: ${chain.error}`}
          <span className="block text-[10px] opacity-70 mt-1">
            This detects edits, deletions and re-ordering of stored rows. It is tamper-evident, not tamper-proof: anyone
            who can rewrite the whole table can recompute the chain.
          </span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by ticket, tool, or rule..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={filterEvent}
            onChange={(e) => setFilterEvent(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700"
          >
            <option value="all">All events</option>
            {EVENT_OPTIONS.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>

          <select
            value={filterActor}
            onChange={(e) => setFilterActor(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700"
          >
            <option value="all">All actors</option>
            <option value="agent">agent</option>
            <option value="human">human</option>
            <option value="system">system</option>
          </select>
        </div>
      </div>

      {error && <ErrorState title="Could not load the audit log" error={error} onRetry={loadAuditLog} />}

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Event</th>
                <th className="py-3 px-4">Ticket</th>
                <th className="py-3 px-4">Tool / Rule</th>
                <th className="py-3 px-4">Result</th>
                <th className="py-3 px-4 text-right">Row hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {filteredEvents.map((ev) => (
                <tr key={ev.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 text-slate-500 font-sans">
                    {timeAgo(ev.timestamp)}
                  </td>
                  <td className="py-3 px-4 font-sans">
                    <span className="font-semibold text-slate-800 capitalize">{ev.actor_type}</span>
                    <span className="text-[10px] text-slate-400 block font-mono">{ev.actor_id}</span>
                  </td>
                  <td className="py-3 px-4 font-semibold text-blue-600">
                    {ev.event}
                  </td>
                  <td className="py-3 px-4 text-slate-700">
                    {ev.ticket_id ? (
                      <Link href={`/tickets/${ev.ticket_id}`} className="hover:underline text-blue-600">
                        {ev.ticket_id.slice(0, 8)}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-800 font-sans">
                    {ev.tool && <span className="font-mono text-emerald-700 font-medium block">{ev.tool}</span>}
                    {ev.policy_rule && <span className="font-mono text-amber-700 text-[10px] block">{ev.policy_rule}</span>}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${resultClass(ev.result_status)}`}>
                      {ev.result_status ?? "n/a"}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-slate-400">
                    <span title={ev.row_hash} className="bg-slate-50 px-1 py-0.5 rounded border border-slate-200">
                      {ev.row_hash?.slice(0, 16)}...
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredEvents.length === 0 && (
          <div className="p-12 text-center text-xs text-slate-500">
            {loading ? "Loading audit log..." : "No audit records match the filters."}
          </div>
        )}
      </div>

    </div>
  );
}
