"use client";

import React from "react";
import { ShieldAlert } from "lucide-react";
import { useApp } from "@/lib/store";

export function KillSwitchBanner() {
  const { killSwitch, toggleKillSwitch, backendReachable } = useApp();

  if (!backendReachable) {
    return (
      <div className="bg-amber-500 text-white px-4 py-2 text-xs font-medium shrink-0">
        Backend unreachable: data shown on this page may be missing or stale.
      </div>
    );
  }

  if (!killSwitch) return null;

  return (
    <div className="bg-red-600 text-white px-4 py-2 text-xs font-medium flex items-center justify-between shadow-md shrink-0">
      <div className="flex items-center gap-2">
        <ShieldAlert className="w-4 h-4 animate-pulse" />
        <span>
          <strong>KILL SWITCH ACTIVE:</strong> the policy gateway rejects all tool executions (step 10).
        </span>
      </div>
      <button
        onClick={() => toggleKillSwitch(false)}
        className="px-3 py-1 rounded bg-white text-red-700 font-semibold text-[11px] hover:bg-red-50 shadow-sm"
      >
        Resume
      </button>
    </div>
  );
}
