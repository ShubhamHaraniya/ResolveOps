"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  GitFork,
  CheckCircle2,
  Clock,
  AlertOctagon,
  ArrowRight,
  ExternalLink,
  Bot,
  Zap,
  Server,
  Code,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { TraceNode } from "@/lib/types";

export default function TracesPage() {
  const { getTraceRun } = useApp();
  const trace = getTraceRun("run-9801-refund")!;
  const [selectedNode, setSelectedNode] = useState<TraceNode | null>(trace.nodes[1]); // default to classify

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              LangGraph Workflow Traces
            </h1>
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
              RUN: {trace.run_id}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Step-by-step state checkpointing, Groq model latency, and deterministic boundary verification
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <Link
            href={`/tickets/${trace.ticket_id}`}
            className="text-blue-600 hover:underline flex items-center gap-1 font-medium"
          >
            Associated Ticket: {trace.ticket_number} &rarr;
          </Link>
        </div>
      </div>

      {/* Trace Overview Header Card */}
      <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
        <div>
          <span className="text-slate-400">Total Duration:</span>
          <div className="font-mono font-bold text-slate-900 mt-0.5">{trace.total_duration_ms} ms</div>
        </div>
        <div>
          <span className="text-slate-400">Total Tokens:</span>
          <div className="font-mono font-bold text-slate-900 mt-0.5">{trace.total_tokens.toLocaleString()}</div>
        </div>
        <div>
          <span className="text-slate-400">Inference Cost:</span>
          <div className="font-mono font-bold text-slate-900 mt-0.5">${trace.total_cost.toFixed(4)}</div>
        </div>
        <div>
          <span className="text-slate-400">Langfuse Trace ID:</span>
          <div className="font-mono text-blue-600 truncate mt-0.5 flex items-center gap-1">
            <span>lf_tr_9801_abc</span>
            <ExternalLink className="w-3 h-3 text-blue-500" />
          </div>
        </div>
      </div>

      {/* Main Grid: Visual Graph Nodes (Left) + Node Inspector Drawer (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Visual Graph Sequence (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              11-Node LangGraph Pipeline
            </span>
            <span className="text-[11px] text-slate-400">Click a node to inspect payload</span>
          </div>

          <div className="space-y-2">
            {trace.nodes.map((node, index) => {
              const isSelected = selectedNode?.id === node.id;
              return (
                <div
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? "border-blue-500 bg-blue-50/40 shadow-xs ring-1 ring-blue-500/20"
                      : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center font-mono text-[10px] font-bold">
                      {index + 1}
                    </span>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-900">
                          {node.name}
                        </span>
                        {node.provider && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 font-mono">
                            {node.provider}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500 truncate max-w-sm">
                        {node.output_summary}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 text-right">
                    <span className="font-mono text-[11px] text-slate-500">
                      {node.latency_ms} ms
                    </span>

                    {node.status === "completed" && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    )}
                    {node.status === "interrupted" && (
                      <Clock className="w-4 h-4 text-amber-500" />
                    )}
                    {node.status === "running" && (
                      <div className="w-3.5 h-3.5 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
                    )}
                    {node.status === "skipped" && (
                      <span className="text-[10px] text-slate-300 font-mono">—</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Node Inspector Drawer (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
          {selectedNode ? (
            <div className="space-y-4">
              <div className="pb-3 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono font-semibold text-slate-400 uppercase">
                    Node Inspector
                  </span>
                  <h3 className="text-sm font-bold text-slate-900 font-mono">
                    {selectedNode.name}
                  </h3>
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                    selectedNode.status === "completed"
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : selectedNode.status === "interrupted"
                      ? "bg-amber-50 text-amber-700 border border-amber-200"
                      : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {selectedNode.status}
                </span>
              </div>

              {/* Node Telemetry */}
              <div className="grid grid-cols-2 gap-2 text-xs p-3 rounded-lg bg-slate-50 border border-slate-200">
                <div>
                  <span className="text-slate-400">Latency:</span>
                  <div className="font-mono font-semibold text-slate-800">{selectedNode.latency_ms} ms</div>
                </div>
                <div>
                  <span className="text-slate-400">Provider:</span>
                  <div className="font-mono font-semibold text-slate-800">{selectedNode.provider || "System"}</div>
                </div>
                {selectedNode.model && (
                  <div className="col-span-2 pt-1 border-t border-slate-200/60 flex justify-between">
                    <span className="text-slate-400">Groq Model:</span>
                    <span className="font-mono text-blue-600">{selectedNode.model}</span>
                  </div>
                )}
                {selectedNode.prompt_tokens && (
                  <div className="col-span-2 flex justify-between">
                    <span className="text-slate-400">Prompt / Completion Tokens:</span>
                    <span className="font-mono text-slate-700">{selectedNode.prompt_tokens} / {selectedNode.completion_tokens}</span>
                  </div>
                )}
              </div>

              {/* Node Input Summary */}
              <div>
                <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  State Input / Trigger
                </label>
                <div className="mt-1 p-2.5 rounded bg-slate-100 font-mono text-[11px] text-slate-700 leading-relaxed">
                  {selectedNode.input_summary || "None"}
                </div>
              </div>

              {/* Node Output Summary */}
              <div>
                <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  State Transformation Output
                </label>
                <div className="mt-1 p-2.5 rounded bg-slate-900 text-slate-100 font-mono text-[11px] leading-relaxed">
                  {selectedNode.output_summary || "Pending execution"}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400">
              Select a node to inspect details.
            </div>
          )}

          <div className="pt-4 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
            <span>LangGraph State Checkpoint: Postgres</span>
            <span className="text-emerald-600 font-mono">Thread ID #9801</span>
          </div>
        </div>
      </div>
    </div>
  );
}
