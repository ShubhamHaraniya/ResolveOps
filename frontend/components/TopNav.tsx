"use client";

import React, { useState } from "react";
import { ShieldCheck, ShieldAlert, AlertTriangle } from "lucide-react";
import { useApp } from "@/lib/store";

export function TopNav() {
  const { killSwitch, toggleKillSwitch } = useApp();
  const [showKillModal, setShowKillModal] = useState(false);
  const [killError, setKillError] = useState<string | null>(null);

  return (
    <>
      <header className="h-14 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0 z-20">
        <div className="flex items-center gap-4 text-xs">
          <span className="font-semibold text-slate-800">ResolveOps</span>
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-100 border border-slate-200 text-slate-600 font-mono text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            Policy gateway: <span className="font-semibold text-slate-800">default-deny</span>
          </div>
        </div>

        {/* Right: kill switch */}
        <div className="flex items-center gap-3">
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
                <span>KILL SWITCH ON</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>Kill switch: off</span>
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
                    ? "Deactivate the kill switch?"
                    : "Activate the kill switch?"}
                </h3>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  {killSwitch
                    ? "Deactivating the kill switch lets the policy gateway execute approved tool calls again."
                    : "While active, the policy gateway rejects every tool execution at step 10 (HTTP 503). The switch is held in the backend process memory and resets when the backend restarts."}
                </p>
                {killError && (
                  <div className="mt-3 text-[11px] text-red-600">{killError}</div>
                )}
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
                onClick={async () => {
                  const err = await toggleKillSwitch(!killSwitch);
                  setKillError(err);
                  if (!err) setShowKillModal(false);
                }}
                className={`px-4 py-2 rounded-md text-xs font-medium text-white transition-all shadow-sm ${
                  killSwitch
                    ? "bg-blue-600 hover:bg-blue-700"
                    : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {killSwitch ? "Deactivate" : "Activate kill switch"}
              </button>
            </div>
          </div>
        </div>
      )}

    </>
  );
}
