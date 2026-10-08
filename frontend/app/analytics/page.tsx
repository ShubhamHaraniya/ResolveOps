"use client";

import React from "react";
import {
  TrendingUp,
  ShieldCheck,
  ShieldAlert,
  Clock,
  DollarSign,
  Activity,
  CheckCircle2,
  Lock,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  AreaChart,
  Area,
} from "recharts";

const CATEGORY_AUTOMATION = [
  { category: "Billing / Invoices", total: 42, automated: 28 },
  { category: "Subscription Tiers", total: 24, automated: 6 },
  { category: "Access & Auth", total: 31, automated: 12 },
  { category: "Usage & Limits", total: 19, automated: 15 },
  { category: "General FAQ", total: 38, automated: 34 },
];

const APPROVAL_OUTCOMES = [
  { name: "Approved As-Is", value: 89, color: "#10b981" },
  { name: "Edited by Reviewer", value: 7, color: "#3b82f6" },
  { name: "Rejected", value: 4, color: "#ef4444" },
];

const FAILURE_REASONS = [
  { reason: "Legal Hold Active", count: 8 },
  { reason: "Adversarial Injection Pattern", count: 14 },
  { reason: "Identity Mismatch (Spoofing)", count: 9 },
  { reason: "Prohibited Admin Role", count: 12 },
  { reason: "Exceeded Dollar Threshold", count: 6 },
];

const COST_TREND = [
  { day: "Oct 1", costPerTicket: 0.0022 },
  { day: "Oct 2", costPerTicket: 0.0021 },
  { day: "Oct 3", costPerTicket: 0.0019 },
  { day: "Oct 4", costPerTicket: 0.0018 },
  { day: "Oct 5", costPerTicket: 0.0019 },
  { day: "Oct 6", costPerTicket: 0.0017 },
  { day: "Oct 7", costPerTicket: 0.0016 },
];

export default function AnalyticsPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Governance & Agent Reliability Analytics
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Empirical measurements across Northwind Cloud evaluation runs and live production traffic
          </p>
        </div>
      </div>

      {/* 12 Key Performance Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <span className="text-[10px] font-semibold text-slate-400 uppercase">Unsafe Actions</span>
          <div className="text-xl font-bold text-emerald-600 font-mono mt-1">0.0%</div>
          <span className="text-[10px] text-slate-400">Target: 0.0%</span>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <span className="text-[10px] font-semibold text-slate-400 uppercase">Duplicate Writes</span>
          <div className="text-xl font-bold text-emerald-600 font-mono mt-1">0</div>
          <span className="text-[10px] text-slate-400">Idempotency 100%</span>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <span className="text-[10px] font-semibold text-slate-400 uppercase">Automation Rate</span>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">34.2%</div>
          <span className="text-[10px] text-emerald-600">&ge; 25% Target</span>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <span className="text-[10px] font-semibold text-slate-400 uppercase">Approval Accept</span>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">89.4%</div>
          <span className="text-[10px] text-emerald-600">&gt; 85% Target</span>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <span className="text-[10px] font-semibold text-slate-400 uppercase">Median Latency</span>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">4.8s</div>
          <span className="text-[10px] text-slate-400">&lt; 20s Target</span>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <span className="text-[10px] font-semibold text-slate-400 uppercase">Avg Cost / Run</span>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">$0.0018</div>
          <span className="text-[10px] text-slate-400">Groq gpt-oss-120b</span>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Automation by Category */}
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <h3 className="text-sm font-semibold text-slate-900">Automation Rate by Category</h3>
          <p className="text-xs text-slate-500 mb-4">Total volume vs autonomously resolved tickets</p>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={CATEGORY_AUTOMATION}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="category" stroke="#94a3b8" fontSize={10} tickLine={false} />
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
                <Bar dataKey="total" fill="#e2e8f0" radius={[2, 2, 0, 0]} name="Total Volume" />
                <Bar dataKey="automated" fill="#3b82f6" radius={[2, 2, 0, 0]} name="Automated" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Approval Outcomes */}
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <h3 className="text-sm font-semibold text-slate-900">Human Approval Disposition</h3>
          <p className="text-xs text-slate-500 mb-4">Reviewer decisions on proposed actions</p>
          <div className="h-64 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={APPROVAL_OUTCOMES}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={85}
                  label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                >
                  {APPROVAL_OUTCOMES.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: Top Intercepted Failure Reasons */}
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <h3 className="text-sm font-semibold text-slate-900">Gateway Security Interceptions</h3>
          <p className="text-xs text-slate-500 mb-4">Distribution of deterministically blocked actions</p>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={FAILURE_REASONS}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                <XAxis type="number" stroke="#94a3b8" fontSize={10} tickLine={false} />
                <YAxis dataKey="reason" type="category" stroke="#94a3b8" fontSize={10} tickLine={false} width={150} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "none",
                    borderRadius: "6px",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="count" fill="#ef4444" radius={[0, 4, 4, 0]} name="Interceptions" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Token Cost per Ticket */}
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <h3 className="text-sm font-semibold text-slate-900">Inference Cost Efficiency</h3>
          <p className="text-xs text-slate-500 mb-4">Average LLM token spend per ticket resolution</p>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={COST_TREND}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="day" stroke="#94a3b8" fontSize={10} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} tickFormatter={(v) => `$${v}`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "none",
                    borderRadius: "6px",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                />
                <Area type="monotone" dataKey="costPerTicket" stroke="#10b981" fill="#10b981" fillOpacity={0.2} name="Cost ($)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
