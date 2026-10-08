"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Search,
  Filter,
  Plus,
  ArrowUpDown,
  ExternalLink,
  ShieldAlert,
  AlertTriangle,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { TierBadge, PriorityBadge, StatusBadge } from "@/components/Badges";
import { formatDate, timeAgo } from "@/lib/utils";
import { ResolutionTier, TicketPriority, TicketStatus } from "@/lib/types";

export default function TicketsListPage() {
  const { tickets } = useApp();
  const [searchQuery, setSearchQuery] = useState("");
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filteredTickets = tickets.filter((ticket) => {
    const matchesSearch =
      ticket.ticket_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.customer.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.category.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesTier = tierFilter === "all" || ticket.tier === tierFilter;
    const matchesPriority = priorityFilter === "all" || ticket.priority === priorityFilter;
    const matchesStatus = statusFilter === "all" || ticket.status === statusFilter;

    return matchesSearch && matchesTier && matchesPriority && matchesStatus;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Support Operations Tickets
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Ingested from Northwind Cloud Zendesk/Intercom mock webhook stream
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-mono">
            Showing {filteredTickets.length} of {tickets.length} tickets
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search tickets, customers, subjects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Filter Dropdowns */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Tier Filter */}
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Tiers</option>
            <option value="auto">Auto Tier</option>
            <option value="approval">Approval Required</option>
            <option value="forbidden">Forbidden</option>
            <option value="escalated">Escalated</option>
          </select>

          {/* Priority Filter */}
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Priorities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Statuses</option>
            <option value="waiting_approval">Waiting Approval</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="blocked">Blocked</option>
          </select>
        </div>
      </div>

      {/* Tickets Data Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                <th className="py-3 px-4">Ticket</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Subject</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Resolution Tier</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4 text-right">Age</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredTickets.map((t) => (
                <tr
                  key={t.id}
                  className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                >
                  <td className="py-3 px-4 font-mono font-semibold text-blue-600">
                    <Link href={`/tickets/${t.id}`} className="hover:underline flex items-center gap-1">
                      {t.ticket_number}
                    </Link>
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-900">
                    <div className="flex items-center gap-1.5">
                      <span>{t.customer.name}</span>
                      {t.customer.is_strategic && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                          STRATEGIC
                        </span>
                      )}
                      {t.customer.is_legal_hold && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded font-semibold bg-red-50 text-red-700 border border-red-200">
                          LEGAL HOLD
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 font-normal">{t.requester_email}</div>
                  </td>
                  <td className="py-3 px-4 text-slate-800 max-w-xs truncate">
                    <Link href={`/tickets/${t.id}`} className="hover:text-blue-600 font-medium block truncate">
                      {t.subject}
                    </Link>
                  </td>
                  <td className="py-3 px-4 text-slate-600 font-mono text-[11px]">
                    {t.category}
                  </td>
                  <td className="py-3 px-4">
                    <PriorityBadge priority={t.priority} />
                  </td>
                  <td className="py-3 px-4">
                    <TierBadge tier={t.tier} />
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={t.status} />
                  </td>
                  <td className="py-3 px-4 font-mono font-medium text-slate-700">
                    {Math.round(t.confidence * 100)}%
                  </td>
                  <td className="py-3 px-4 text-right text-slate-400 font-mono text-[11px]">
                    {timeAgo(t.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredTickets.length === 0 && (
          <div className="p-8 text-center text-xs text-slate-500">
            No tickets found matching current search and filters.
          </div>
        )}
      </div>
    </div>
  );
}
