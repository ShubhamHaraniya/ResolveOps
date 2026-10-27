"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  Server,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { useApp } from "@/lib/store";

export default function SettingsPage() {
  const { killSwitch, toggleKillSwitch, systemHealth, backendReachable, refresh } = useApp();
  const [refreshing, setRefreshing] = useState(false);
  const [killError, setKillError] = useState<string | null>(null);

  const recheck = async () => {
    setRefreshing(true);
    await refresh();
    setRefreshing(false);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-slate-200">
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          System & Governance Settings
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Gateway kill switch, model defaults, and backend dependency status
        </p>
      </div>

      {/* Safety & Emergency Kill Switch Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-lg ${
                killSwitch ? "bg-red-100 text-red-600" : "bg-emerald-50 text-emerald-600"
              }`}
            >
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Global Policy Gateway Kill Switch
              </h3>
              <p className="text-xs text-slate-500">
                Reject every tool execution at the policy gateway until released.
              </p>
            </div>
          </div>

          <button
            onClick={async () => setKillError(await toggleKillSwitch(!killSwitch))}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all shadow-xs ${
              killSwitch
                ? "bg-red-600 text-white hover:bg-red-700 animate-pulse"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {killSwitch ? "Kill switch ON (click to release)" : "Kill switch off (click to engage)"}
          </button>
        </div>

        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
          When active, the policy gateway rejects tool executions at <strong>step 10</strong> with HTTP 503. The switch is held in backend process memory: it resets on restart and is not shared across workers.
        </div>
        {killError && <div className="text-xs text-red-600">{killError}</div>}
      </div>

      {/* AI Inference Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Cpu className="w-4 h-4 text-slate-500" />
          <h3 className="text-sm font-bold text-slate-900">
            Groq Models (defaults)
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50 space-y-1.5">
            <span className="text-[10px] font-semibold text-slate-400 uppercase">
              Primary Planning Model
            </span>
            <div className="font-mono font-bold text-slate-900 text-sm">
              openai/gpt-oss-120b
            </div>
            <p className="text-[11px] text-slate-500">
              Default for action planning (<code>GROQ_MODEL_PRIMARY</code>).
            </p>
          </div>

          <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50 space-y-1.5">
            <span className="text-[10px] font-semibold text-slate-400 uppercase">
              Fast Classifier Model
            </span>
            <div className="font-mono font-bold text-slate-900 text-sm">
              openai/gpt-oss-20b
            </div>
            <p className="text-[11px] text-slate-500">
              Default for ticket classification (<code>GROQ_MODEL_FAST</code>).
            </p>
          </div>
        </div>
      </div>

      {/* Connected Subsystem Health & Diagnostics */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-slate-500" />
            <h3 className="text-sm font-bold text-slate-900">
              Backend Dependencies
            </h3>
          </div>
          <button
            onClick={recheck}
            disabled={refreshing}
            className="px-3 py-1 rounded border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-medium flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
            <span>{refreshing ? "Checking..." : "Re-check"}</span>
          </button>
        </div>

        <div className="divide-y divide-slate-100 text-xs">
          {!backendReachable && (
            <div className="py-3 text-amber-600">Backend unreachable.</div>
          )}
          {systemHealth.map((svc) => (
            <div key={svc.name} className="py-3 flex items-center gap-3">
              {svc.status === "healthy" ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-500" />
              )}
              <div>
                <div className="font-semibold text-slate-800">{svc.name}</div>
                <div className="text-[11px] text-slate-400">
                  Status: {svc.status}
                  {svc.latency_ms !== null && ` · ${svc.latency_ms} ms`}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
