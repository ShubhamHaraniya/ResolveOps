"use client";

import React from "react";
import { Sparkles, X, ShieldAlert, ArrowRight } from "lucide-react";
import { useApp } from "@/lib/store";
import { useRouter } from "next/navigation";
import { MOCK_DEMO_SCENARIOS } from "@/lib/mockData";

export function DemoBanner() {
  const router = useRouter();
  const { demoBannerVisible, dismissDemoBanner, runScenario } = useApp();

  if (!demoBannerVisible) return null;

  return (
    <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white px-4 py-2 text-xs border-b border-indigo-900/50 flex flex-wrap items-center justify-between gap-2 shadow-sm shrink-0">
      <div className="flex items-center gap-2.5">
        <span className="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-indigo-400" />
          DEMO MODE
        </span>
        <span className="text-slate-300 font-medium">
          Northwind Cloud FDE Engagement: Simulated 1,800 tickets/mo with deterministic LangGraph policy governance.
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-[11px] text-slate-400 hidden lg:inline">Quick Test:</span>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {MOCK_DEMO_SCENARIOS.slice(0, 3).map((sc) => (
            <button
              key={sc.id}
              onClick={() => {
                runScenario(sc.id);
                router.push(`/tickets/${sc.ticket_id}`);
              }}
              className="px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-slate-200 hover:text-white transition-all text-[11px] font-medium border border-white/10"
            >
              {sc.name.split(" ")[0]} ({sc.ticket_id.toUpperCase()})
            </button>
          ))}
        </div>

        <button
          onClick={dismissDemoBanner}
          className="p-1 rounded text-slate-400 hover:text-slate-200 ml-2"
          title="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

export function KillSwitchBanner() {
  const { killSwitch, toggleKillSwitch } = useApp();

  if (!killSwitch) return null;

  return (
    <div className="bg-red-600 text-white px-4 py-2 text-xs font-medium flex items-center justify-between shadow-md animate-in slide-in-from-top duration-200 shrink-0">
      <div className="flex items-center gap-2">
        <ShieldAlert className="w-4 h-4 animate-pulse" />
        <span>
          <strong>GLOBAL EMERGENCY KILL SWITCH ACTIVATED:</strong> All automated agent tool executions and financial writes are hard-blocked by Policy Gateway Step 10.
        </span>
      </div>
      <button
        onClick={() => toggleKillSwitch(false)}
        className="px-3 py-1 rounded bg-white text-red-700 font-semibold text-[11px] hover:bg-red-50 shadow-sm"
      >
        Resume Gateway
      </button>
    </div>
  );
}
