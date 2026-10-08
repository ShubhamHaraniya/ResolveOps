"use client";

import React, { useState } from "react";
import {
  BookOpen,
  AlertTriangle,
  FileText,
  CheckCircle2,
  Clock,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";

interface KBDoc {
  id: string;
  name: string;
  version: string;
  status: "active" | "deprecated";
  lastUpdated: string;
  owner: string;
  description: string;
  content: string;
}

const KB_DOCS: KBDoc[] = [
  {
    id: "refund-v3",
    name: "Northwind Cloud Customer Refund Policy",
    version: "v3.1",
    status: "active",
    lastUpdated: "2026-10-01",
    owner: "Finance & Operations Policy Guild",
    description: "Current operational guidelines for duplicate billing, cancellations, and SLA outage compensations.",
    content: `## 1. Scope & Objective
This policy defines the authority limits and authorization gates for issuing customer financial refunds and credits across Northwind Cloud billing accounts.

## 2. Refund Thresholds & Authorization Tiers
* **Tier 1 (Automated):** Informational lookups and zero-dollar ledger corrections may be auto-executed by AI agents.
* **Tier 2 (Under $100):** Duplicate billing charges or over-usage errors under $100 require one human sign-off from a **Support Agent**.
* **Tier 3 ($100 - $1,000):** Pro-rated subscription cancellations or hardware credits between $100 and $1,000 require **Support Lead** authorization.
* **Tier 4 (Above $1,000):** High-dollar refunds require **Director of Finance** sign-off.
* **Hard Block:** Any single refund exceeding $50,000 is permanently forbidden from AI workflow pipelines.

## 3. Account Freeze Conditions
Accounts flagged under active **Compliance Legal Hold** (Policy GEN-001) are prohibited from receiving any refund, credit, or ledger modifications until legal release is registered.`,
  },
  {
    id: "refund-v2",
    name: "Northwind Cloud Customer Refund Policy (Legacy)",
    version: "v2.0",
    status: "deprecated",
    lastUpdated: "2025-06-15",
    owner: "Finance & Legal",
    description: "Deprecated legacy policy. Superseded by v3.1. Maintained in knowledge base to evaluate conflict detection.",
    content: `## 1. Legacy Refund Rules (DEPRECATED)
* In v2.0, support agents had unilateral authority to issue refunds up to $250 without secondary manager approval.
* Outage credits were calculated on a flat $50 credit voucher rather than pro-rated SLA percentage.

> WARNING: This document was superseded on 2026-10-01. Any agent plan citing v2.0 thresholds will trigger a Policy Conflict Warning.`,
  },
  {
    id: "access-v1",
    name: "IAM Role & Access Assignment Governance",
    version: "v1.4",
    status: "active",
    lastUpdated: "2026-09-20",
    owner: "Security Operations",
    description: "Access boundary specifications governing role elevation and temporary credential generation.",
    content: `## 1. Zero-Trust Access Restrictions
Under Policy ACC-099, autonomous AI agents and delegated support tools are strictly barred from granting administrative privileges:
* Role \`prod-admin\` is permanently forbidden.
* Role \`org-admin\` is permanently forbidden.
* Direct private key exfiltration or unverified email delivery is blocked at the schema validation boundary.

## 2. Allowed Delegations
* Agents may generate temporary viewer tokens for verified organization contacts after MFA challenge completion.`,
  },
];

export default function KnowledgeBasePage() {
  const [selectedDoc, setSelectedDoc] = useState<KBDoc>(KB_DOCS[0]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Policy Knowledge Base & RAG Index
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Vector embeddings indexed in Qdrant with dense retrieval and cross-encoder reranking
          </p>
        </div>
      </div>

      {/* Policy Conflict Warning Banner */}
      <div className="p-4 rounded-xl border border-amber-300 bg-amber-50/70 flex items-start gap-3 shadow-xs">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs">
          <div className="font-semibold text-amber-900 flex items-center gap-2">
            <span>Policy Conflict Detection Active</span>
            <span className="font-mono text-[10px] px-2 py-0.2 rounded bg-amber-200 text-amber-800 font-bold">
              POL-CONFLICT-01
            </span>
          </div>
          <p className="text-amber-800 mt-1 leading-relaxed">
            Both <strong>v2.0</strong> and <strong>v3.1</strong> of the Refund Policy are indexed in the vector store. The ResolveOps Policy Gateway deterministically flags citations citing deprecated documents and enforces the latest active version (v3.1).
          </p>
        </div>
      </div>

      {/* Main Grid: Document List + Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Document List (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-1">
            Indexed Policy Documents
          </div>
          {KB_DOCS.map((doc) => {
            const isSelected = selectedDoc.id === doc.id;
            return (
              <div
                key={doc.id}
                onClick={() => setSelectedDoc(doc)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? "bg-white border-blue-500 shadow-sm ring-1 ring-blue-500/20"
                    : "bg-white border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                      doc.status === "active"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : "bg-slate-100 text-slate-500 border border-slate-200"
                    }`}
                  >
                    {doc.status.toUpperCase()} ({doc.version})
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {doc.lastUpdated}
                  </span>
                </div>
                <h3 className="text-xs font-bold text-slate-900 line-clamp-1">
                  {doc.name}
                </h3>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                  {doc.description}
                </p>
              </div>
            );
          })}
        </div>

        {/* Document Viewer (8 cols) */}
        <div className="lg:col-span-8 bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 mb-6">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-slate-900">
                    {selectedDoc.name}
                  </h2>
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
                    {selectedDoc.version}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Custodian: {selectedDoc.owner} · Updated {selectedDoc.lastUpdated}
                </p>
              </div>

              {selectedDoc.status === "active" ? (
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Active Policy
                </span>
              ) : (
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  Deprecated Document
                </span>
              )}
            </div>

            <div className="prose prose-slate max-w-none text-xs leading-relaxed whitespace-pre-wrap font-sans text-slate-800">
              {selectedDoc.content}
            </div>
          </div>

          <div className="mt-8 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="font-mono text-[11px]">
              Qdrant Collection: <code>northwind_policies</code> (Cosine Metric)
            </span>
            <span className="text-blue-600 font-medium">Chunk size: 512 tokens · Overlap: 64</span>
          </div>
        </div>
      </div>
    </div>
  );
}
