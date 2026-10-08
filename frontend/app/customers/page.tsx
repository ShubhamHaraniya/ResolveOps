"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Building,
  Search,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  CreditCard,
  DollarSign,
  ArrowRight,
} from "lucide-react";
import { MOCK_CUSTOMERS } from "@/lib/mockData";
import { formatCurrency } from "@/lib/utils";

export default function CustomersPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [planFilter, setPlanFilter] = useState("all");

  const filteredCustomers = MOCK_CUSTOMERS.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.owner.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPlan = planFilter === "all" || c.plan === planFilter;
    return matchesSearch && matchesPlan;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Customer Organizations
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Northwind Cloud B2B tenant records synchronized from Salesforce CRM MCP
          </p>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search organizations, domains, owners..."
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
          <option value="all">All Plans</option>
          <option value="Enterprise">Enterprise</option>
          <option value="Growth">Growth</option>
          <option value="Starter">Starter</option>
        </select>
      </div>

      {/* Customers Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                <th className="py-3 px-4">Organization</th>
                <th className="py-3 px-4">Domain</th>
                <th className="py-3 px-4">Plan</th>
                <th className="py-3 px-4">ARR</th>
                <th className="py-3 px-4">Governance Tags</th>
                <th className="py-3 px-4">Account Owner</th>
                <th className="py-3 px-4">CSM</th>
                <th className="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredCustomers.map((cust) => (
                <tr key={cust.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3.5 px-4 font-semibold text-slate-900">
                    <div className="flex items-center gap-2">
                      <Building className="w-4 h-4 text-slate-400" />
                      <span>{cust.name}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-600">
                    {cust.domain}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-100 text-slate-700 font-medium">
                      {cust.plan}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                    {formatCurrency(cust.arr)}
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-1.5">
                      {cust.is_strategic && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                          STRATEGIC
                        </span>
                      )}
                      {cust.is_legal_hold && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-red-50 text-red-700 border border-red-200 flex items-center gap-1">
                          <ShieldAlert className="w-3 h-3 text-red-600" />
                          LEGAL HOLD
                        </span>
                      )}
                      {!cust.is_strategic && !cust.is_legal_hold && (
                        <span className="text-slate-400 text-[11px]">—</span>
                      )}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-slate-700">{cust.owner}</td>
                  <td className="py-3.5 px-4 text-slate-700">{cust.csm}</td>
                  <td className="py-3.5 px-4 text-right">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Active
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
