"use client";

import React, { useCallback, useEffect, useState } from "react";
import { RotateCw, Sparkles } from "lucide-react";
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
} from "recharts";
import { ErrorState } from "@/components/States";

const TOOLTIP_STYLE = {
  backgroundColor: "#0f172a",
  border: "none",
  borderRadius: "6px",
  color: "#fff",
  fontSize: "12px",
};

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "n/a" : `${v}%`);
const score = (v: number | null | undefined) =>
  v === null || v === undefined ? "n/a" : `${(v * 100).toFixed(1)}%`;

function Kpi({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
      <span className="text-[10px] font-semibold text-slate-400 uppercase">{label}</span>
      <div className="text-xl font-bold text-slate-900 font-mono mt-1">{value}</div>
      <span className="text-[10px] text-slate-400">{note}</span>
    </div>
  );
}

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<any>(null);
  const [ragas, setRagas] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [runningBenchmark, setRunningBenchmark] = useState<boolean>(false);
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null);

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const [ovRes, ragasRes] = await Promise.all([
        fetch("/api/analytics/overview", { cache: "no-store" }),
        fetch("/api/analytics/ragas", { cache: "no-store" }),
      ]);
      if (!ovRes.ok) throw new Error(`overview: HTTP ${ovRes.status}`);
      setMetrics(await ovRes.json());
      if (ragasRes.ok) {
        const r = await ragasRes.json();
        setRagas(r.status === "no_report" ? null : r);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const runBenchmark = async () => {
    setRunningBenchmark(true);
    setBenchmarkError(null);
    try {
      const res = await fetch("/api/analytics/ragas/run", { method: "POST" });
      const data = await res.json();
      if (data.status === "completed" && data.report) setRagas(data.report);
      else setBenchmarkError(data.message ?? `Benchmark failed (HTTP ${res.status})`);
    } catch (err) {
      setBenchmarkError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setRunningBenchmark(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
    const interval = setInterval(loadAnalytics, 10000);
    return () => clearInterval(interval);
  }, [loadAnalytics]);

  if (error && !metrics) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <ErrorState title="Could not load analytics" error={error} onRetry={loadAnalytics} />
      </div>
    );
  }
  if (!metrics) return <div className="p-8 text-xs text-slate-400">Loading...</div>;

  const categoryData = metrics.category_automation ?? [];
  const approvalData = (metrics.approval_outcomes ?? []).filter((o: any) => o.value > 0);
  const ragMetrics = ragas?.metrics ?? {};

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Analytics</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Ticket and approval figures come from the database. Latency, cost and security counters only cover the{" "}
            {metrics.runs_sampled} run(s) held in backend memory since its last start. &quot;n/a&quot; means no data yet.
          </p>
        </div>
        <button
          onClick={loadAnalytics}
          className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs flex items-center gap-1.5 transition-colors self-start sm:self-auto"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-blue-600" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <Kpi label="Tickets" value={String(metrics.total_tickets)} note={`${metrics.resolved_tickets} resolved`} />
        <Kpi label="Resolution Rate" value={pct(metrics.automation_rate)} note="resolved / all tickets" />
        <Kpi label="Escalation Rate" value={pct(metrics.escalation_rate)} note="escalated / all tickets" />
        <Kpi label="Approval Rate" value={pct(metrics.approval_acceptance_rate)} note="approved / decided" />
        <Kpi
          label="Planning Latency"
          value={metrics.median_proposal_latency_ms === null ? "n/a" : `${metrics.median_proposal_latency_ms} ms`}
          note={metrics.p95_proposal_latency_ms === null ? "median" : `median · p95 ${metrics.p95_proposal_latency_ms} ms`}
        />
        <Kpi
          label="LLM Cost / Run"
          value={metrics.cost_per_ticket_usd === null ? "n/a" : `$${Number(metrics.cost_per_ticket_usd).toFixed(4)}`}
          note="estimated, mean"
        />
        <Kpi label="Forbidden Actions" value={String(metrics.blocked_actions)} note="policy tier: forbidden" />
        <Kpi label="Injection Flags" value={String(metrics.injection_attempt_count)} note="runs flagged" />
        <Kpi label="Gateway Denials" value={String(metrics.gateway_denials)} note="tool calls rejected" />
      </div>

      <div className="rounded-xl border border-indigo-200/80 bg-white p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-indigo-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">RAG benchmark (LLM-judged)</h2>
            <p className="text-xs text-slate-600 mt-1">
              Retrieval quality over a small golden query set against the policy documents. Scores are produced by an
              LLM judge, so running it needs a Groq API key; they are indicative, not a formal evaluation.
              {ragas && ` Last run: ${new Date(ragas.timestamp).toLocaleString()} (${ragas.total_test_queries} queries).`}
            </p>
          </div>
          <button
            onClick={runBenchmark}
            disabled={runningBenchmark}
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold flex items-center gap-2 shadow-xs transition-colors disabled:opacity-50 self-start sm:self-auto cursor-pointer"
          >
            <Sparkles className={`w-3.5 h-3.5 ${runningBenchmark ? "animate-spin" : ""}`} />
            <span>{runningBenchmark ? "Running..." : "Run benchmark"}</span>
          </button>
        </div>

        {benchmarkError && (
          <div className="mt-3 px-3 py-2 rounded border border-red-200 bg-red-50 text-xs text-red-800">{benchmarkError}</div>
        )}

        {!ragas ? (
          <p className="mt-4 text-xs text-slate-500">No benchmark report yet.</p>
        ) : (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mt-4">
              <Kpi label="Overall" value={score(ragas.ragas_score)} note="combined score" />
              <Kpi label="Faithfulness" value={score(ragMetrics.faithfulness)} note={`target ${score(ragas.target_thresholds?.faithfulness)}`} />
              <Kpi label="Answer Relevance" value={score(ragMetrics.answer_relevance)} note={`target ${score(ragas.target_thresholds?.answer_relevance)}`} />
              <Kpi label="Context Precision" value={score(ragMetrics.context_precision)} note={`target ${score(ragas.target_thresholds?.context_precision)}`} />
              <Kpi label="Context Recall" value={score(ragMetrics.context_recall)} note={`target ${score(ragas.target_thresholds?.context_recall)}`} />
            </div>

            {ragas.dataset_results?.length > 0 && (
              <div className="mt-5 border border-slate-200/80 rounded-lg overflow-hidden bg-white">
                <div className="overflow-x-auto max-h-56 overflow-y-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-[10px] uppercase font-semibold text-slate-500 border-b border-slate-200 sticky top-0">
                      <tr>
                        <th className="px-3 py-2">Test</th>
                        <th className="px-3 py-2">Query</th>
                        <th className="px-3 py-2">Expected doc</th>
                        <th className="px-3 py-2">Precision</th>
                        <th className="px-3 py-2">Faithfulness</th>
                        <th className="px-3 py-2">Top citation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                      {ragas.dataset_results.map((row: any) => (
                        <tr key={row.test_id} className="hover:bg-slate-50/60">
                          <td className="px-3 py-1.5 font-bold text-indigo-600">{row.test_id}</td>
                          <td className="px-3 py-1.5 font-sans text-slate-800 max-w-xs truncate">{row.query}</td>
                          <td className="px-3 py-1.5 text-slate-600">{row.expected_doc}</td>
                          <td className="px-3 py-1.5">{score(row.context_precision)}</td>
                          <td className="px-3 py-1.5">{score(row.faithfulness)}</td>
                          <td className="px-3 py-1.5 text-slate-500">{row.top_citation}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <h3 className="text-sm font-semibold text-slate-900">Tickets by category group</h3>
          <p className="text-xs text-slate-500 mb-4">Total tickets vs. tickets with status resolved</p>
          {categoryData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-xs text-slate-400">No tickets yet.</div>
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="category" stroke="#94a3b8" fontSize={10} tickLine={false} />
                  <YAxis allowDecimals={false} stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="total" fill="#6366f1" radius={[4, 4, 0, 0]} name="Total" />
                  <Bar dataKey="automated" fill="#10b981" radius={[4, 4, 0, 0]} name="Resolved" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs">
          <h3 className="text-sm font-semibold text-slate-900">Approval outcomes</h3>
          <p className="text-xs text-slate-500 mb-4">Stored approval requests by final status</p>
          {approvalData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-xs text-slate-400">No decided approvals yet.</div>
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={approvalData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={85}
                    label={({ name, value }) => `${name} (${value})`}
                  >
                    {approvalData.map((entry: any) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
