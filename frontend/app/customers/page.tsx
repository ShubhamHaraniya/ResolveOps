"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Building, Search, ShieldAlert } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { EmptyState, ErrorState, SkeletonTable } from "@/components/States";

interface Customer {
  id: string;
  name: string;
  plan: string | null;
  arr_cents: number;
  is_strategic: boolean;
  is_legal_hold: boolean;
  csm_owner: string | null;
  status: string | null;
  contact_count: number;
  ticket_count: number;
}

const PLANS = ["starter", "pro", "enterprise", "enterprise_plus"];

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [planFilter, setPlanFilter] = useState("all");

  const load = useCallback(async () => {
    setError(null);
    try {
      const qs = new URLSearchParams({ page_size: "200" });
      if (planFilter !== "all") qs.set("plan", planFilter);
      const res = await fetch(`/api/customers?${qs}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setCustomers((await res.json()).customers);
    } catch (e) {
      setCustomers(null);
      setError(e instanceof Error ? e.message : "Request failed");
    }
  }, [planFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const q = searchQuery.toLowerCase();
  const filtered = (customers ?? []).filter(
    (c) => c.name.toLowerCase().includes(q) || (c.csm_owner ?? "").toLowerCase().includes(q)
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="pb-2 border-b border-slate-200">
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Customer Accounts</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Accounts stored in the ResolveOps database (read-only view)
        </p>
      </div>

      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by account or CSM..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:border-blue-500"
          />
        </div>

        <select
          value={planFilter}
          onChange={(e) => setPlanFilter(e.target.value)}
          className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none"
        >
          <option value="all">All plans</option>
          {PLANS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorState title="Could not load customers" error={error} onRetry={load} />
      ) : customers === null ? (
        <SkeletonTable rows={5} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No accounts"
          description="No accounts match. A fresh database is seeded with the sample accounts on first backend start."
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                  <th className="py-3 px-4">Account</th>
                  <th className="py-3 px-4">Plan</th>
                  <th className="py-3 px-4">ARR</th>
                  <th className="py-3 px-4">Flags</th>
                  <th className="py-3 px-4">CSM</th>
                  <th className="py-3 px-4">Contacts</th>
                  <th className="py-3 px-4">Tickets</th>
                  <th className="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-slate-900">
                      <div className="flex items-center gap-2">
                        <Building className="w-4 h-4 text-slate-400" />
                        <span>{c.name}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-100 text-slate-700 font-medium">
                        {c.plan}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                      {formatCurrency(c.arr_cents / 100)}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5">
                        {c.is_strategic && (
                          <span className="px-1.5 rounded text-[9px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                            STRATEGIC
                          </span>
                        )}
                        {c.is_legal_hold && (
                          <span className="px-1.5 rounded text-[9px] font-bold bg-red-50 text-red-700 border border-red-200 flex items-center gap-1">
                            <ShieldAlert className="w-3 h-3 text-red-600" />
                            LEGAL HOLD
                          </span>
                        )}
                        {!c.is_strategic && !c.is_legal_hold && (
                          <span className="text-slate-400 text-[11px]">—</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-700">{c.csm_owner ?? "—"}</td>
                    <td className="py-3.5 px-4 text-slate-700">{c.contact_count}</td>
                    <td className="py-3.5 px-4 text-slate-700">{c.ticket_count}</td>
                    <td className="py-3.5 px-4 text-right text-slate-600">{c.status ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
