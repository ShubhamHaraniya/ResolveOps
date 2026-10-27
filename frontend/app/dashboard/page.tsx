"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  CheckCircle,
  Clock,
  Server,
  Zap,
  Ticket as TicketIcon,
  Activity,
  ShieldAlert,
  RotateCw,
} from "lucide-react";
import { timeAgo } from "@/lib/utils";
import { useApp } from "@/lib/store";
import { ErrorState } from "@/components/States";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface Overview {
  automation_rate: number | null;
  approval_acceptance_rate: number | null;
  escalation_rate: number | null;
  median_proposal_latency_ms: number | null;
  cost_per_ticket_usd: number | null;
  injection_attempt_count: number;
  blocked_actions: number;
  gateway_denials: number;
  total_tickets: number;
  resolved_tickets: number;
  awaiting_approval_count: number;
  category_automation: { category: string; total: number; automated: number; rate: number | null }[];
  approval_outcomes: { name: string; value: number; color: string }[];
  runs_sampled: number;
}

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "n/a" : `${v}%`);

const resultClass = (status?: string | null) => {
  const v = (status ?? "").toLowerCase();
  if (v.includes("denied") || v.includes("fail") || v.includes("error") || v.includes("block") || v.includes("reject")) {
    return "bg-red-50 text-red-700 border border-red-200";
  }
  return v ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-slate-50 text-slate-500 border border-slate-200";
};

const TOOLTIP_STYLE = {
  backgroundColor: "#0f172a",
  border: "none",
  borderRadius: "6px",
  color: "#fff",
  fontSize: "12px",
};

export default function DashboardPage() {
  const { systemHealth } = useApp();
  const [metrics, setMetrics] = useState<Overview | null>(null);
  const [auditFeed, setAuditFeed] = useState<any[]>([]);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      const [mRes, aRes, apRes] = await Promise.all([
        fetch("/api/analytics/overview", { cache: "no-store" }),
        fetch("/api/audit?page_size=6", { cache: "no-store" }),
        fetch("/api/approvals?status=pending", { cache: "no-store" }),
      ]);
      if (!mRes.ok) throw new Error(`overview: HTTP ${mRes.status}`);
      setMetrics(await mRes.json());
      if (aRes.ok) setAuditFeed((await aRes.json()).events ?? []);
      if (apRes.ok) setPendingApprovalsCount((await apRes.json()).total ?? 0);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 10000);
    return () => clearInterval(interval);
  }, [loadDashboardData]);

  if (error && !metrics) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <ErrorState title="Could not load the dashboard" error={error} onRetry={loadDashboardData} />
      </div>
    );
  }

  if (!metrics) {
    return <div className="p-8 text-xs text-slate-400">Loading...</div>;
  }

  const outcomes = metrics.approval_outcomes.filter((o) => o.value > 0);
  const categories = metrics.category_automation.map((c) => ({ ...c, rate: c.rate ?? 0 }));

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Operations Overview</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Computed from stored tickets and approvals. Latency, cost and security counters only cover runs held in
            backend memory since its last start ({metrics.runs_sampled} run{metrics.runs_sampled === 1 ? "" : "s"}).
          </p>
        </div>

        <button
          onClick={loadDashboardData}
          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs flex items-center gap-1.5 transition-colors"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-blue-600" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Tickets</span>
            <TicketIcon className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{metrics.total_tickets}</div>
          <div className="mt-2 text-[11px] text-slate-500">
            {metrics.resolved_tickets} resolved · {metrics.awaiting_approval_count} awaiting approval
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Resolution Rate</span>
            <Zap className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{pct(metrics.automation_rate)}</div>
          <div className="mt-2 text-[11px] text-slate-500">Resolved tickets / all tickets</div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Approval Rate</span>
            <CheckCircle className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{pct(metrics.approval_acceptance_rate)}</div>
          <div className="mt-2 text-[11px] text-slate-500">Approved / (approved + rejected)</div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Planning Latency</span>
            <Clock className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {metrics.median_proposal_latency_ms === null ? "n/a" : `${metrics.median_proposal_latency_ms} ms`}
          </div>
          <div className="mt-2 text-[11px] text-slate-500">Median plan_action node time</div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Blocked / Flagged</span>
            <ShieldAlert className="w-4 h-4 text-red-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{metrics.blocked_actions}</div>
          <div className="mt-2 text-[11px] text-slate-500">
            Forbidden actions · {metrics.injection_attempt_count} injection flag(s) · {metrics.gateway_denials} gateway denial(s)
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <h3 className="text-sm font-semibold text-slate-900">Approval outcomes</h3>
          <p className="text-xs text-slate-500 mb-4">Stored approval requests by final status</p>
          {outcomes.length === 0 ? (
            <div className="h-56 flex items-center justify-center text-xs text-slate-400">No decided approvals yet.</div>
          ) : (
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={outcomes}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis allowDecimals={false} stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="value" name="Approvals" radius={[2, 2, 0, 0]}>
                    {outcomes.map((o) => (
                      <Cell key={o.name} fill={o.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <h3 className="text-sm font-semibold text-slate-900">Resolution rate by category</h3>
          <p className="text-xs text-slate-500 mb-4">Resolved tickets as a share of tickets per category group</p>
          {categories.length === 0 ? (
            <div className="h-56 flex items-center justify-center text-xs text-slate-400">No tickets yet.</div>
          ) : (
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categories}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="category" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis domain={[0, 100]} unit="%" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="rate" name="Resolved %" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-4">
          <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <Server className="w-4 h-4 text-slate-500" />
            Dependencies
          </h3>
          <div className="divide-y divide-slate-100 text-xs">
            {systemHealth.length === 0 && <div className="py-2.5 text-slate-400">No status available.</div>}
            {systemHealth.map((svc) => (
              <div key={svc.name} className="py-2.5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${svc.status === "healthy" ? "bg-emerald-500" : "bg-amber-500"}`} />
                  <span className="font-medium text-slate-700">{svc.name}</span>
                </div>
                <span className="font-mono text-[11px] text-slate-500">
                  {svc.status === "healthy" ? (svc.latency_ms !== null ? `${svc.latency_ms} ms` : "up") : "unreachable"}
                </span>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-slate-400">Redis and Qdrant are optional; the app falls back without them.</p>
        </div>

        <div className="lg:col-span-2 p-5 rounded-xl border border-slate-200 bg-white shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-blue-600" />
                  Latest audit events
                </h3>
                <p className="text-xs text-slate-500">Newest entries of the hash-chained audit log</p>
              </div>
              <Link href="/audit" className="text-xs text-blue-600 font-medium hover:underline">
                View full audit log &rarr;
              </Link>
            </div>

            <div className="divide-y divide-slate-100 text-xs">
              {auditFeed.length === 0 ? (
                <div className="py-6 text-center text-slate-400">No audit events recorded yet.</div>
              ) : (
                auditFeed.map((ev, i) => (
                  <div key={ev.id || i} className="py-2.5 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold shrink-0 ${resultClass(ev.result_status)}`}>
                        {ev.result_status ?? "n/a"}
                      </span>
                      <div className="truncate">
                        <span className="font-semibold text-slate-800 mr-2">{(ev.event || "").replace(/_/g, " ")}</span>
                        {ev.policy_rule && <span className="font-mono text-[10px] text-slate-500 mr-2">[{ev.policy_rule}]</span>}
                        {ev.tool && <span className="font-mono text-[11px] text-blue-600">{ev.tool}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 text-slate-400 text-[11px]">
                      {ev.ticket_id && (
                        <Link href={`/tickets/${ev.ticket_id}`} className="text-slate-600 hover:text-blue-600 font-mono text-[10px] underline">
                          {ev.ticket_id.slice(0, 8)}
                        </Link>
                      )}
                      <span>{timeAgo(ev.timestamp)}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex justify-end text-xs">
            <Link href="/approvals" className="text-blue-600 font-medium hover:underline">
              {pendingApprovalsCount} approval(s) pending &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
