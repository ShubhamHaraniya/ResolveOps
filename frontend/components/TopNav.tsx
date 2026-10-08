"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  PlayCircle,
  X,
  ExternalLink,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { useRouter } from "next/navigation";
import { MOCK_DEMO_SCENARIOS } from "@/lib/mockData";

export function TopNav() {
  const router = useRouter();
  const { killSwitch, toggleKillSwitch, runScenario, resetDemoData } = useApp();
  const [showKillModal, setShowKillModal] = useState(false);
  const [showDemoModal, setShowDemoModal] = useState(false);

  const handleLaunchScenario = (scenarioId: string, ticketId: string) => {
    runScenario(scenarioId);
    setShowDemoModal(false);
    router.push(`/tickets/${ticketId}`);
  };

  return (
    <>
      <header className="h-14 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0 z-20">
        {/* Left: Context & Tenant */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-800">Northwind Cloud Operations</span>
            <span className="text-slate-300">/</span>
            <span className="text-slate-500 font-mono text-[11px]">Production (simulated)</span>
          </div>

          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-100 border border-slate-200 text-slate-600 font-mono text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            Policy Gateway: <span className="font-semibold text-slate-800">Enforcing (Default-Deny)</span>
          </div>
        </div>

        {/* Right: Actions, Demo Launcher, Kill Switch */}
        <div className="flex items-center gap-3">
          {/* Quick Demo Scenarios trigger */}
          <button
            onClick={() => setShowDemoModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-medium hover:bg-indigo-100 transition-colors shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Simulate FDE Scenarios</span>
          </button>

          {/* Reset Demo State button */}
          <button
            onClick={resetDemoData}
            title="Reset to initial demo data"
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          {/* Global Kill Switch trigger */}
          <button
            onClick={() => setShowKillModal(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              killSwitch
                ? "bg-red-600 text-white shadow-md shadow-red-500/30 animate-pulse"
                : "bg-slate-100 text-slate-700 hover:bg-red-50 hover:text-red-700 hover:border-red-200 border border-slate-200"
            }`}
          >
            {killSwitch ? (
              <>
                <ShieldAlert className="w-3.5 h-3.5 text-white" />
                <span>KILL SWITCH ACTIVE</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>Kill Switch (Standby)</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Kill Switch Modal */}
      {showKillModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start gap-4">
              <div
                className={`p-3 rounded-full shrink-0 ${
                  killSwitch ? "bg-amber-100 text-amber-600" : "bg-red-100 text-red-600"
                }`}
              >
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-slate-900">
                  {killSwitch
                    ? "Resume Autonomous Gateway Execution?"
                    : "Activate Global Emergency Kill Switch?"}
                </h3>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  {killSwitch
                    ? "Deactivating the kill switch will restore normal autonomous agent evaluation and allow approved side-effect executions across MCP backends."
                    : "Activating the kill switch immediately halts all outgoing writes and API calls at Step 10 of the Policy Gateway. Any pending approval execution will be strictly rejected with a security interrupt."}
                </p>
                <div className="mt-4 p-3 rounded bg-slate-50 border border-slate-200 text-[11px] font-mono text-slate-700">
                  Security Event: <span className="font-semibold">{killSwitch ? "SEC-DEACTIVATE-KILL" : "SEC-HALT-ALL-WRITES"}</span>
                </div>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowKillModal(false)}
                className="px-4 py-2 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  toggleKillSwitch(!killSwitch);
                  setShowKillModal(false);
                }}
                className={`px-4 py-2 rounded-md text-xs font-medium text-white transition-all shadow-sm ${
                  killSwitch
                    ? "bg-blue-600 hover:bg-blue-700"
                    : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {killSwitch ? "Deactivate & Resume Gateway" : "Confirm Emergency Halt"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Demo Scenario Modal */}
      {showDemoModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-2xl w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
                  <PlayCircle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900">
                    Live Demo Scenario Launcher
                  </h3>
                  <p className="text-xs text-slate-500">
                    Select any simulated scenario to inspect the deterministic policy boundary in action.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowDemoModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[60vh] overflow-y-auto p-1">
              {MOCK_DEMO_SCENARIOS.map((sc) => (
                <div
                  key={sc.id}
                  onClick={() => handleLaunchScenario(sc.id, sc.ticket_id)}
                  className="p-3.5 rounded-lg border border-slate-200 hover:border-blue-500 hover:shadow-md transition-all cursor-pointer bg-white group flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-semibold text-xs text-slate-900 group-hover:text-blue-600 transition-colors">
                        {sc.name}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                        {sc.ticket_id.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed mb-3">
                      {sc.description}
                    </p>
                  </div>
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                    <span className="text-slate-500 font-mono text-[10px] truncate max-w-[200px]">
                      {sc.expected_outcome}
                    </span>
                    <span className="text-blue-600 font-medium group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                      Launch &rarr;
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
