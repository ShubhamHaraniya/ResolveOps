import React from "react";
import { ResolutionTier, TicketPriority, TicketStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CheckCircle2, Clock, AlertOctagon, ArrowUpRight } from "lucide-react";

export function TierBadge({ tier, className }: { tier: ResolutionTier; className?: string }) {
  switch (tier) {
    case "auto":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200",
            className
          )}
        >
          <CheckCircle2 className="w-3 h-3 text-blue-600" />
          Auto Tier
        </span>
      );
    case "approval":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200",
            className
          )}
        >
          <Clock className="w-3 h-3 text-amber-600" />
          Approval Required
        </span>
      );
    case "forbidden":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-red-50 text-red-700 border border-red-200",
            className
          )}
        >
          <AlertOctagon className="w-3 h-3 text-red-600" />
          Forbidden Action
        </span>
      );
    case "escalated":
      return (
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-orange-50 text-orange-700 border border-orange-200",
            className
          )}
        >
          <ArrowUpRight className="w-3 h-3 text-orange-600" />
          Escalated to Human
        </span>
      );
    default:
      return null;
  }
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  const styles: Record<TicketPriority, string> = {
    low: "bg-slate-100 text-slate-600 border-slate-200",
    medium: "bg-blue-50 text-blue-700 border-blue-200",
    high: "bg-amber-50 text-amber-800 border-amber-200",
    urgent: "bg-red-50 text-red-700 border-red-200 font-bold",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border uppercase tracking-wider",
        styles[priority]
      )}
    >
      {priority}
    </span>
  );
}

export function StatusBadge({ status }: { status: TicketStatus }) {
  const styles: Record<TicketStatus, { bg: string; dot: string; label: string }> = {
    open: { bg: "bg-slate-100 text-slate-700 border-slate-200", dot: "bg-slate-400", label: "Open" },
    in_progress: { bg: "bg-blue-50 text-blue-700 border-blue-200", dot: "bg-blue-500", label: "In Progress" },
    waiting_approval: { bg: "bg-amber-50 text-amber-700 border-amber-200", dot: "bg-amber-500", label: "Waiting Approval" },
    resolved: { bg: "bg-emerald-50 text-emerald-700 border-emerald-200", dot: "bg-emerald-500", label: "Resolved" },
    blocked: { bg: "bg-red-50 text-red-700 border-red-200", dot: "bg-red-500", label: "Blocked" },
  };

  const current = styles[status] || styles.open;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border",
        current.bg
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full", current.dot)} />
      {current.label}
    </span>
  );
}
