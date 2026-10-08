"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  TrendingUp,
  Clock,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  Server,
  Zap,
  Ticket as TicketIcon,
  Activity,
  ShieldAlert,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { formatCurrency, timeAgo } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
} from "recharts";

const TIER_DATA = [
  { day: "Mon", auto: 24, approval: 18, forbidden: 6, escalated: 4 },
  { day: "Tue", auto: 29, approval: 22, forbidden: 4, escalated: 5 },
  { day: "Wed", auto: 31, approval: 19, forbidden: 8, escalated: 3 },
  { day: "Thu", auto: 38, approval: 25, forbidden: 5, escalated: 6 },
  { day: "Fri", auto: 42, approval: 28, forbidden: 7, escalated: 4 },
  { day: "Sat", auto: 15, approval: 10, forbidden: 2, escalated: 2 },
  { day: "Sun", auto: 18, approval: 12, forbidden: 3, escalated: 1 },
];

const AUTOMATION_TREND = [
  { day: "Oct 1", rate: 26.5 },
  { day: "Oct 2", rate: 28.0 },
  { day: "Oct 3", rate: 29.4 },
  { day: "Oct 4", rate: 31.8 },
  { day: "Oct 5", rate: 33.1 },
  { day: "Oct 6", rate: 32.5 },
  { day: "Oct 7", rate: 34.2 },
];

const LATENCY_TREND = [
  { time: "08:00", p50: 3.8, p95: 7.2 },
  { time: "10:00", p50: 4.2, p95: 8.5 },
  { time: "12:00", p50: 5.1, p95: 9.8 },
  { time: "14:00", p50: 4.6, p95: 8.1 },
  { time: "16:00", p50: 4.4, p95: 7.9 },
  { time: "18:00", p50: 3.9, p95: 6.8 },
];

export default function DashboardPage() {
  const { tickets, approvals, auditLog, systemHealth, killSwitch } = useApp();
  const [timeRange, setTimeRange] = useState("Today");

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            Operations Telemetry
            <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
              LIVE
            </span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Northwind Cloud · 1,800 monthly ticket volume run-rate · LangGraph governed loop
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-200 shadow-xs">
          {["Today", "7 Days", "30 Days"].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                timeRange === range
                  ? "bg-slate-900 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* 5 KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Metric 1 */}
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Tickets Today</span>
            <TicketIcon className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900">58</div>
          <div className="mt-2 flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>+14% vs yesterday</span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Automation Rate</span>
            <Zap className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">34.2%</div>
          <div className="mt-2 text-[11px] text-slate-500 font-medium flex items-center justify-between">
            <span>Target: &ge; 25%</span>
            <span className="text-emerald-600 font-semibold">&check; Compliant</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Approval Acceptance</span>
            <CheckCircle className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">89.4%</div>
          <div className="mt-2 text-[11px] text-slate-500 font-medium flex items-center justify-between">
            <span>Target: &gt; 85%</span>
            <span className="text-emerald-600 font-semibold">&check; Compliant</span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Median Proposal Time</span>
            <Clock className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">4.8s</div>
          <div className="mt-2 text-[11px] text-slate-500 font-medium flex items-center justify-between">
            <span>Target: &lt; 20s</span>
            <span className="text-emerald-600 font-semibold">&check; 4x Faster</span>
          </div>
        </div>

        {/* Metric 5 */}
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-medium">Unsafe Actions</span>
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-600">0</div>
          <div className="mt-2 text-[11px] text-slate-500 font-medium flex items-center justify-between">
            <span>Target: 0</span>
            <span className="text-emerald-600 font-semibold font-mono">100% Safe</span>
          </div>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart 1: Tier Breakdown */}
        <div className="lg:col-span-2 p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Ticket Resolution Volume by Tier
              </h3>
              <p className="text-xs text-slate-500">
                Auto-executed vs. Human Approval vs. Forbidden Gateways
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-sm bg-blue-500" /> Auto
              </span>
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-sm bg-amber-500" /> Approval
              </span>
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-sm bg-red-500" /> Forbidden
              </span>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={TIER_DATA}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="day" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "none",
                    borderRadius: "6px",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="auto" fill="#3b82f6" radius={[2, 2, 0, 0]} name="Auto Tier" />
                <Bar dataKey="approval" fill="#f59e0b" radius={[2, 2, 0, 0]} name="Approval Required" />
                <Bar dataKey="forbidden" fill="#ef4444" radius={[2, 2, 0, 0]} name="Forbidden" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Automation Trend */}
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-semibold text-slate-900">Automation Trajectory</h3>
              <span className="text-xs font-mono font-bold text-blue-600">34.2%</span>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Autonomous ticket resolution rate over the last 7 days
            </p>
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={AUTOMATION_TREND}>
                  <defs>
                    <linearGradient id="colorRate" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="day" stroke="#94a3b8" fontSize={10} tickLine={false} />
                  <YAxis domain={[20, 40]} stroke="#94a3b8" fontSize={10} tickLine={false} unit="%" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border: "none",
                      borderRadius: "6px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="rate"
                    stroke="#2563eb"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorRate)"
                    name="Automation %"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Autonomous Goal</span>
            <span className="font-semibold text-slate-700">Target &gt; 25.0% reached</span>
          </div>
        </div>
      </div>

      {/* System Health Grid & Recent Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* System Health Subpanel */}
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <Server className="w-4 h-4 text-slate-500" />
              Connected Subsystems
            </h3>
            <span className="text-[11px] font-mono text-emerald-600 font-medium">All Healthy</span>
          </div>
          <div className="divide-y divide-slate-100 text-xs">
            {systemHealth.map((svc) => (
              <div key={svc.name} className="py-2.5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="font-medium text-slate-700">{svc.name}</span>
                </div>
                <div className="flex items-center gap-3 font-mono text-[11px] text-slate-500">
                  <span>{svc.latency_ms} ms</span>
                  <span className="text-[10px] text-slate-400">{svc.last_check}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
            <strong>Groq Orchestration:</strong> Fast primary inference running via{" "}
            <code className="text-blue-600 font-mono">openai/gpt-oss-120b</code>. Deterministic policy gateway verifies all tool invocations prior to dispatch.
          </div>
        </div>

        {/* Recent Activity Audit Timeline */}
        <div className="lg:col-span-2 p-5 rounded-xl border border-slate-200 bg-white shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-blue-600" />
                  Live Policy Enforcement Feed
                </h3>
                <p className="text-xs text-slate-500">
                  Latest security gate decisions, approval requests, and read-back verifications
                </p>
              </div>
              <Link
                href="/audit"
                className="text-xs text-blue-600 font-medium hover:underline flex items-center gap-1"
              >
                View Full Audit Log &rarr;
              </Link>
            </div>

            <div className="divide-y divide-slate-100 text-xs">
              {auditLog.slice(0, 6).map((ev) => (
                <div key={ev.id} className="py-2.5 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold shrink-0 ${
                        ev.result_status === "SUCCESS"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : ev.result_status === "BLOCKED"
                          ? "bg-red-50 text-red-700 border border-red-200"
                          : ev.result_status === "INTERRUPTED"
                          ? "bg-amber-50 text-amber-700 border border-amber-200"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {ev.result_status}
                    </span>

                    <div className="truncate">
                      <span className="font-semibold text-slate-800 mr-2">
                        {ev.event.replace(/_/g, " ").toUpperCase()}
                      </span>
                      {ev.policy_rule && (
                        <span className="font-mono text-[10px] text-slate-500 mr-2">
                          [{ev.policy_rule}]
                        </span>
                      )}
                      {ev.tool && (
                        <span className="font-mono text-[11px] text-blue-600">
                          {ev.tool}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 text-slate-400 text-[11px]">
                    <Link
                      href={`/tickets/${ev.ticket_id}`}
                      className="text-slate-600 hover:text-blue-600 font-mono text-[10px] underline"
                    >
                      {ev.ticket_id}
                    </Link>
                    <span>{timeAgo(ev.timestamp)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5 font-mono text-[11px] text-emerald-700">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Cryptographic Hash Chain: Intact (SHA-256 Verified)
            </span>
            <Link
              href="/approvals"
              className="text-blue-600 font-medium hover:underline flex items-center gap-1"
            >
              {approvals.length} Approvals Pending &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
