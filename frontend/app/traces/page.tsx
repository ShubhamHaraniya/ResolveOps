"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { CheckCircle2, Clock, AlertOctagon, RotateCw, ChevronDown } from "lucide-react";
import { TraceNode, TraceRun } from "@/lib/types";
import { EmptyState, ErrorState } from "@/components/States";

function statusLabel(status: string): string {
  return status === "awaiting_approval" ? "Awaiting approval" : status.replace(/_/g, " ");
}

function statusClass(status: string): string {
  if (status === "done" || status === "completed") return "bg-emerald-50 text-emerald-700 border border-emerald-200";
  if (status === "awaiting_approval" || status === "paused" || status === "running")
    return "bg-amber-50 text-amber-700 border border-amber-200";
  if (status === "failed") return "bg-red-50 text-red-700 border border-red-200";
  return "bg-slate-100 text-slate-600 border border-slate-200";
}

function fmtMs(ms: number | null | undefined): string {
  return ms === null || ms === undefined ? "n/a" : `${ms} ms`;
}

export default function TracesPage() {
  const [runs, setRuns] = useState<TraceRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const params = useParams<{ runId?: string }>();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(params?.runId ?? null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/runs?limit=50", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRuns(data.runs ?? []);
      setSelectedRunId((prev) => prev ?? data.runs?.[0]?.run_id ?? null);
    } catch (e) {
      setRuns(null);
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  if (error) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <ErrorState title="Could not load workflow runs" error={error} onRetry={fetchRuns} />
      </div>
    );
  }

  if (runs !== null && runs.length === 0) {
    return (
      <div className="p-8 max-w-7xl mx-auto space-y-4">
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Workflow Runs</h1>
        <EmptyState
          title="No workflow runs yet"
          description="Create a ticket from the Tickets page; each ticket starts a LangGraph run that will show up here."
        />
      </div>
    );
  }

  const trace = runs?.find((r) => r.run_id === selectedRunId) ?? null;
  if (!trace) {
    return <div className="p-8 text-xs text-slate-400">Loading...</div>;
  }
  const selectedNode: TraceNode | null =
    trace.nodes.find((n) => n.id === selectedNodeId) ?? trace.nodes[0] ?? null;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Workflow Runs</h1>
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
              {trace.run_id}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-mono font-bold capitalize ${statusClass(trace.status)}`}>
              {statusLabel(trace.status)}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Node timeline of each LangGraph run. Nodes marked Groq call the LLM; all others are deterministic.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="text-slate-500 font-medium">Run:</span>
          <div className="relative">
            <select
              value={trace.run_id}
              onChange={(e) => {
                setSelectedRunId(e.target.value);
                setSelectedNodeId(null);
              }}
              className="pl-3 pr-8 py-1.5 text-xs font-mono font-medium rounded-lg border border-slate-300 bg-white shadow-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer"
            >
              {runs?.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.ticket_number ?? r.run_id.slice(0, 8)} — {(r.subject ?? "").slice(0, 32)} ({statusLabel(r.status)})
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
          </div>

          <button
            onClick={fetchRuns}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors"
            title="Refresh runs"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-blue-600" : ""}`} />
          </button>

          {trace.ticket_id && (
            <Link href={`/tickets/${trace.ticket_id}`} className="text-blue-600 hover:underline font-medium ml-2">
              Ticket {trace.ticket_number} &rarr;
            </Link>
          )}
        </div>
      </div>

      <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
        <div>
          <span className="text-slate-400">Total duration</span>
          <div className="font-mono font-bold text-slate-900 mt-0.5">{fmtMs(trace.total_duration_ms)}</div>
        </div>
        <div>
          <span className="text-slate-400">LLM calls</span>
          <div className="font-mono font-bold text-slate-900 mt-0.5">{trace.llm_calls ?? "n/a"}</div>
        </div>
        <div>
          <span className="text-slate-400">Estimated LLM cost</span>
          <div className="font-mono font-bold text-slate-900 mt-0.5">
            {trace.total_cost === null ? "n/a" : `$${trace.total_cost.toFixed(4)}`}
          </div>
        </div>
        <div>
          <span className="text-slate-400">Langfuse trace ID</span>
          <div className="font-mono text-slate-700 truncate mt-0.5">{trace.langfuse_trace_id ?? "not recorded"}</div>
        </div>
      </div>

      {trace.error && (
        <div className="px-4 py-3 rounded-lg border border-red-200 bg-red-50 text-xs text-red-800">
          Run error: {trace.error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Node timeline ({trace.nodes.length})
            </span>
            <span className="text-[11px] text-slate-400">Click a node to inspect</span>
          </div>

          <div className="space-y-2">
            {trace.nodes.length === 0 && <div className="text-xs text-slate-400">No nodes recorded for this run.</div>}
            {trace.nodes.map((node, index) => {
              const isSelected = selectedNode?.id === node.id;
              return (
                <div
                  key={node.id}
                  onClick={() => setSelectedNodeId(node.id)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? "border-blue-500 bg-blue-50/40 shadow-xs ring-1 ring-blue-500/20"
                      : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center font-mono text-[10px] font-bold shrink-0">
                      {index + 1}
                    </span>
                    <span className="font-mono text-xs font-bold text-slate-900">{node.name}</span>
                    {node.provider && (
                      <span className="text-[10px] px-1.5 rounded bg-slate-100 text-slate-600 font-mono shrink-0">
                        {node.provider}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="font-mono text-[11px] text-slate-500">{fmtMs(node.latency_ms)}</span>
                    {node.status === "completed" && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                    {node.status === "paused" && <Clock className="w-4 h-4 text-amber-500" />}
                    {node.status === "failed" && <AlertOctagon className="w-4 h-4 text-red-500" />}
                    {node.status === "running" && (
                      <div className="w-3.5 h-3.5 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
                    )}
                    {(node.status === "skipped" || node.status === "pending") && (
                      <span className="text-[10px] text-slate-300 font-mono">{node.status}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          {selectedNode ? (
            <div className="space-y-4">
              <div className="pb-3 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono font-semibold text-slate-400 uppercase">Node</span>
                  <h3 className="text-sm font-bold text-slate-900 font-mono">{selectedNode.name}</h3>
                </div>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${statusClass(selectedNode.status)}`}>
                  {statusLabel(selectedNode.status)}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs p-3 rounded-lg bg-slate-50 border border-slate-200">
                <div>
                  <span className="text-slate-400">Latency</span>
                  <div className="font-mono font-semibold text-slate-800">{fmtMs(selectedNode.latency_ms)}</div>
                </div>
                <div>
                  <span className="text-slate-400">Type</span>
                  <div className="font-mono font-semibold text-slate-800">{selectedNode.provider ?? "n/a"}</div>
                </div>
              </div>

              {selectedNode.error && (
                <div className="p-2.5 rounded bg-red-50 border border-red-200 font-mono text-[11px] text-red-800">
                  {selectedNode.error}
                </div>
              )}
              <p className="text-[11px] text-slate-400">
                Per-node inputs and outputs are not recorded in the run timeline.
              </p>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400">Select a node to inspect details.</div>
          )}
        </div>
      </div>
    </div>
  );
}
