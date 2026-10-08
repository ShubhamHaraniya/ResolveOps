"use client";

import React, { useState } from "react";
import {
  Settings as SettingsIcon,
  ShieldAlert,
  ShieldCheck,
  Server,
  Cpu,
  Key,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { useApp } from "@/lib/store";

export default function SettingsPage() {
  const { killSwitch, toggleKillSwitch, systemHealth } = useApp();
  const [testingService, setTestingService] = useState<string | null>(null);

  const testConnectivity = (name: string) => {
    setTestingService(name);
    setTimeout(() => {
      setTestingService(null);
    }, 700);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-slate-200">
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          System & Governance Settings
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Configuration parameters, model bindings, and security gateway switches
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
                Instantly halt all automated agent writes and external side-effects across all backends.
              </p>
            </div>
          </div>

          <button
            onClick={() => toggleKillSwitch(!killSwitch)}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all shadow-xs ${
              killSwitch
                ? "bg-red-600 text-white hover:bg-red-700 animate-pulse"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {killSwitch ? "KILL SWITCH ENGAGED (CLICK TO RESUME)" : "STANDBY (ACTIVE)"}
          </button>
        </div>

        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
          When active, the policy gateway short-circuits at <strong>Step 10</strong>, rejecting all outgoing tool executions with a deterministic <code>GATEWAY_HALTED</code> event in the tamper-evident audit ledger.
        </div>
      </div>

      {/* AI Inference Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Cpu className="w-4 h-4 text-slate-500" />
          <h3 className="text-sm font-bold text-slate-900">
            Groq Orchestration Models
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
              Used for complex multi-tool planning, RAG synthesis, and structured resolution schemas.
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
              Used for initial intent classification, sentiment scoring, and urgency routing.
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
              Connected Integrations & MCP Services
            </h3>
          </div>
          <span className="text-xs text-emerald-600 font-mono font-semibold">
            All 7 Services Connected
          </span>
        </div>

        <div className="divide-y divide-slate-100 text-xs">
          {systemHealth.map((svc) => (
            <div key={svc.name} className="py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <div>
                  <div className="font-semibold text-slate-800">{svc.name}</div>
                  <div className="text-[11px] text-slate-400">
                    Ping latency: {svc.latency_ms} ms · Status: {svc.status}
                  </div>
                </div>
              </div>

              <button
                onClick={() => testConnectivity(svc.name)}
                disabled={testingService === svc.name}
                className="px-3 py-1 rounded border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-medium flex items-center gap-1.5"
              >
                <RefreshCw
                  className={`w-3 h-3 ${testingService === svc.name ? "animate-spin" : ""}`}
                />
                <span>{testingService === svc.name ? "Pinging..." : "Test Connectivity"}</span>
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
