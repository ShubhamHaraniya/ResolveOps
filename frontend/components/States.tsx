import React from "react";
import { AlertOctagon, AlertTriangle, Inbox, RefreshCw, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("p-5 rounded-lg border border-slate-200 bg-white animate-pulse", className)}>
      <div className="h-4 w-1/3 bg-slate-200 rounded mb-3" />
      <div className="h-8 w-1/2 bg-slate-200 rounded mb-2" />
      <div className="h-3 w-3/4 bg-slate-100 rounded" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="border border-slate-200 rounded-lg bg-white overflow-hidden animate-pulse">
      <div className="h-10 bg-slate-100 border-b border-slate-200 flex items-center px-4">
        <div className="h-4 w-1/4 bg-slate-200 rounded" />
      </div>
      <div className="divide-y divide-slate-100">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="p-4 flex items-center gap-4">
            <div className="h-4 w-12 bg-slate-200 rounded" />
            <div className="h-4 w-32 bg-slate-200 rounded" />
            <div className="h-4 flex-1 bg-slate-100 rounded" />
            <div className="h-4 w-20 bg-slate-200 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function EmptyState({
  title = "No items found",
  description = "There are no records matching your current filter criteria.",
  icon: Icon = Inbox,
  action,
}: {
  title?: string;
  description?: string;
  icon?: any;
  action?: React.ReactNode;
}) {
  return (
    <div className="p-12 text-center flex flex-col items-center justify-center border border-dashed border-slate-200 rounded-lg bg-white/50">
      <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <p className="mt-1 text-xs text-slate-500 max-w-sm">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ForbiddenState({
  title = "Action Prohibited by Policy",
  rule = "GEN-001 / ACC-099",
  reason = "This operation was intercepted and forbidden by the deterministic policy gateway.",
}: {
  title?: string;
  rule?: string;
  reason?: string;
}) {
  return (
    <div className="p-6 rounded-lg border border-red-200 bg-red-50/50 flex items-start gap-4">
      <div className="p-2.5 rounded-lg bg-red-100 text-red-600 shrink-0">
        <ShieldAlert className="w-6 h-6" />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold text-red-900">{title}</h4>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-red-200/60 text-red-800 font-bold">
            {rule}
          </span>
        </div>
        <p className="mt-1.5 text-xs text-red-700 leading-relaxed">{reason}</p>
      </div>
    </div>
  );
}

export function DegradedState({
  service = "Billing Backend",
  details = "Simulated latency or transient failure detected. Read-back verification active.",
}: {
  service?: string;
  details?: string;
}) {
  return (
    <div className="p-4 rounded-lg border border-amber-200 bg-amber-50/60 flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
      <div>
        <h5 className="text-xs font-semibold text-amber-900">Degraded Service: {service}</h5>
        <p className="text-xs text-amber-700 mt-0.5">{details}</p>
      </div>
    </div>
  );
}

export function ErrorState({
  title = "Failed to load data",
  error = "Connection refused or gateway timeout",
  onRetry,
}: {
  title?: string;
  error?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="p-8 text-center border border-red-200 rounded-lg bg-white">
      <AlertOctagon className="w-8 h-8 text-red-500 mx-auto mb-2" />
      <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
      <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">{error}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-900 text-white text-xs font-medium hover:bg-slate-800"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry
        </button>
      )}
    </div>
  );
}
