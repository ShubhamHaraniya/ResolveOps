"use client";

import React from "react";
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
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApp } from "@/lib/store";

export function Sidebar() {
  const pathname = usePathname();
  const { approvals, systemHealth, killSwitch } = useApp();

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Tickets", href: "/tickets", icon: TicketIcon },
    {
      label: "Approvals",
      href: "/approvals",
      icon: CheckCircle2,
      badge: approvals.length > 0 ? approvals.length : undefined,
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
              Northwind Cloud AI Agent
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

      {/* Connected Systems Status */}
      <div className="p-3 border-t border-[#1e293b] bg-[#070d1e]/60">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Server className="w-3 h-3 text-emerald-400" />
            Connected Systems
          </span>
          <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            7 / 7 UP
          </span>
        </div>
        <div className="grid grid-cols-2 gap-1 text-[10px]">
          {systemHealth.slice(0, 6).map((svc) => (
            <div
              key={svc.name}
              className="px-2 py-1 rounded bg-[#0f172a] border border-[#1e293b]/70 flex items-center justify-between text-slate-300 truncate"
              title={`${svc.name}: ${svc.latency_ms}ms`}
            >
              <span className="truncate pr-1 text-[10px] text-slate-400">{svc.name.split(" ")[0]}</span>
              <span className="text-emerald-400 font-mono text-[9px]">{svc.latency_ms}ms</span>
            </div>
          ))}
        </div>
        <div className="mt-2 text-[10px] text-slate-500 flex items-center justify-between pt-1 border-t border-slate-800/80">
          <span>Groq gpt-oss-120b</span>
          <span className="text-blue-400 font-mono">140ms</span>
        </div>
      </div>
    </aside>
  );
}
