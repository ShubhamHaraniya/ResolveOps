"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Ticket as TicketIcon,
  CheckCircle2,
  Users,
  BookOpen,
  History,
  BarChart3,
  GitFork,
  Settings as SettingsIcon,
  ShieldAlert,
  Server,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApp } from "@/lib/store";

export function Sidebar() {
  const pathname = usePathname();
  const { systemHealth, killSwitch, backendReachable } = useApp();
  const [livePendingCount, setLivePendingCount] = useState<number | undefined>(undefined);

  useEffect(() => {
    let isMounted = true;
    const fetchPending = async () => {
      try {
        const res = await fetch("/api/approvals?status=pending", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          const count = data.total !== undefined ? data.total : (data.approvals?.length || 0);
          if (isMounted) {
            setLivePendingCount(count > 0 ? count : undefined);
          }
        }
      } catch {
        // keep prior count
      }
    };

    fetchPending();
    const interval = setInterval(fetchPending, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Tickets", href: "/tickets", icon: TicketIcon },
    {
      label: "Approvals",
      href: "/approvals",
      icon: CheckCircle2,
      badge: livePendingCount,
      badgeColor: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    },
    { label: "Customers", href: "/customers", icon: Users },
    { label: "Knowledge Base", href: "/knowledge-base", icon: BookOpen },
    { label: "Audit Log", href: "/audit", icon: History },
    { label: "Analytics", href: "/analytics", icon: BarChart3 },
    { label: "Traces", href: "/traces", icon: GitFork },
    { label: "Settings", href: "/settings", icon: SettingsIcon },
  ];

  return (
    <aside className="w-64 bg-[#0b1329] border-r border-[#1e293b] flex flex-col h-screen select-none shrink-0 z-30">
      {/* Brand Header */}
      <div className="p-5 border-b border-[#1e293b] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20 text-sm">
            RO
          </div>
          <div>
            <div className="text-white font-semibold text-sm tracking-tight flex items-center gap-1.5">
              ResolveOps
              <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">
                GOVERNED
              </span>
            </div>
            <p className="text-slate-400 text-[11px] leading-tight">
              Governed support operations
            </p>
          </div>
        </div>
      </div>

      {/* Emergency Kill Switch Status indicator if active */}
      {killSwitch && (
        <div className="mx-3 mt-3 p-2.5 rounded-md bg-red-950/80 border border-red-500/50 flex items-center gap-2 text-red-200 text-xs">
          <ShieldAlert className="w-4 h-4 text-red-400 shrink-0 animate-pulse" />
          <span className="font-medium text-[11px]">GATEWAY HALTED (KILL SWITCH)</span>
        </div>
      )}

      {/* Navigation List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          Operations
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-all group",
                isActive
                  ? "bg-blue-600/15 text-blue-400 border border-blue-500/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-[#152243]"
              )}
            >
              <div className="flex items-center gap-2.5">
                <Icon
                  className={cn(
                    "w-4 h-4 transition-colors",
                    isActive ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300"
                  )}
                />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span
                  className={cn(
                    "px-1.5 py-0.2 rounded-full text-[10px] font-semibold",
                    item.badgeColor
                  )}
                >
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Backend dependency status (from /ready) */}
      <div className="p-3 border-t border-[#1e293b] bg-[#070d1e]/60">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Server className="w-3 h-3 text-slate-400" />
            Dependencies
          </span>
          {!backendReachable && (
            <span className="text-[10px] text-amber-400 font-mono">backend offline</span>
          )}
        </div>
        <div className="space-y-1 text-[10px]">
          {systemHealth.length === 0 && backendReachable && (
            <div className="text-slate-500">Loading...</div>
          )}
          {systemHealth.map((svc) => (
            <div
              key={svc.name}
              className="px-2 py-1 rounded bg-[#0f172a] border border-[#1e293b]/70 flex items-center justify-between text-slate-300"
            >
              <span className="truncate pr-1 text-slate-400">{svc.name}</span>
              <span
                className={cn(
                  "font-mono text-[9px]",
                  svc.status === "healthy" ? "text-emerald-400" : "text-amber-400"
                )}
              >
                {svc.status === "healthy" ? "up" : "down"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
