"use client";

import React, { useState, useEffect } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  RotateCw,
  Plus,
  Edit3,
  Save,
  Search,
} from "lucide-react";

interface PolicyItem {
  id: string;
  filename: string;
  name: string;
  version: string;
  status: "active" | "deprecated";
  size_bytes: number;
  updated_at: string;
  snippet?: string;
  content?: string;
}

export default function KnowledgeBasePage() {
  const [policies, setPolicies] = useState<PolicyItem[]>([]);
  const [selectedPolicy, setSelectedPolicy] = useState<PolicyItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [reindexing, setReindexing] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Editor states
  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [editTitle, setEditTitle] = useState("");
  const [editVersion, setEditVersion] = useState("v1.0");
  const [editStatus, setEditStatus] = useState<"active" | "deprecated">("active");
  const [saving, setSaving] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadPolicies = async (selectId?: string) => {
    try {
      setLoading(true);
      const res = await fetch("/api/policies", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        const list: PolicyItem[] = data.policies || [];
        setPolicies(list);
        if (list.length > 0) {
          const targetId = selectId || selectedPolicy?.id || list[0].id;
          fetchPolicyDetail(targetId);
        }
      }
    } catch (err) {
      console.warn("Failed to load policies:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPolicyDetail = async (id: string) => {
    try {
      const res = await fetch(`/api/policies/${id}`, { cache: "no-store" });
      if (res.ok) {
        const doc = await res.json();
        setSelectedPolicy(doc);
      }
    } catch (err) {
      console.warn("Failed to load policy detail:", err);
    }
  };

  useEffect(() => {
    loadPolicies();
  }, []);

  const handleReindex = async () => {
    try {
      setReindexing(true);
      const res = await fetch("/api/policies/reindex", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        showToast(data.message || "Vector index successfully synchronized!");
        loadPolicies(selectedPolicy?.id);
      } else {
        showToast("Reindexing failed");
      }
    } catch (err) {
      console.error(err);
      showToast("Error triggering reindex");
    } finally {
      setReindexing(false);
    }
  };

  const startEdit = () => {
    if (!selectedPolicy) return;
    setEditTitle(selectedPolicy.name);
    setEditContent(selectedPolicy.content || "");
    setEditVersion(selectedPolicy.version || "v1.0");
    setEditStatus(selectedPolicy.status || "active");
    setIsEditing(true);
  };

  const saveEdit = async () => {
    if (!selectedPolicy) return;
    try {
      setSaving(true);
      const res = await fetch(`/api/policies/${selectedPolicy.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editTitle,
          content: editContent,
          version: editVersion,
          status: editStatus,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`Saved and re-indexed ${data.chunks_indexed} vector chunks!`);
        setIsEditing(false);
        loadPolicies(selectedPolicy.id);
      } else {
        showToast("Failed to save changes");
      }
    } catch (err) {
      console.error(err);
      showToast("Network error while saving");
    } finally {
      setSaving(false);
    }
  };

  const startCreate = () => {
    setEditTitle("");
    setEditContent(`# New Operational Policy\n\n## 1. Scope & Objective\nDefine policy scope and requirements.\n\n## 2. Authorization Thresholds\n* **Tier 1:** Standard requests.\n* **Tier 2:** Escalations required.`);
    setEditVersion("v1.0");
    setEditStatus("active");
    setIsCreating(true);
  };

  const saveCreate = async () => {
    if (!editTitle.trim()) {
      showToast("Please enter a policy title");
      return;
    }
    try {
      setSaving(true);
      const res = await fetch("/api/policies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editTitle,
          content: editContent,
          version: editVersion,
          status: editStatus,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`Policy '${data.filename}' created and indexed into Qdrant & BM25!`);
        setIsCreating(false);
        loadPolicies(data.id);
      } else {
        const errData = await res.json().catch(() => ({}));
        showToast(errData.detail || "Failed to create policy");
      }
    } catch (err) {
      console.error(err);
      showToast("Network error creating policy");
    } finally {
      setSaving(false);
    }
  };

  const filteredPolicies = policies.filter((p) => {
    const q = searchQuery.toLowerCase();
    return (
      p.name.toLowerCase().includes(q) ||
      p.filename.toLowerCase().includes(q) ||
      p.id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Toast */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-lg border border-slate-700 text-xs flex items-center gap-2 animate-in fade-in slide-in-from-bottom-3">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Policy Knowledge Base & RAG Vector Engine
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
              {policies.length} POLICIES INDEXED
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Real markdown policies parsed, embedded with FastEmbed (BGE-Small), and indexed into Qdrant & BM25
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={startCreate}
            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Policy</span>
          </button>

          <button
            onClick={handleReindex}
            disabled={reindexing}
            className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
          >
            <RotateCw className={`w-3.5 h-3.5 ${reindexing ? "animate-spin text-blue-600" : ""}`} />
            <span>{reindexing ? "Re-indexing..." : "Re-index All"}</span>
          </button>
        </div>
      </div>

      {/* Policy Conflict Warning Banner */}
      <div className="p-4 rounded-xl border border-amber-300 bg-amber-50/70 flex items-start gap-3 shadow-xs">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs">
          <div className="font-semibold text-amber-900 flex items-center gap-2">
            <span>Policy Conflict Detection & Active Precedence Engine</span>
            <span className="font-mono text-[10px] px-2 py-0.2 rounded bg-amber-200 text-amber-800 font-bold">
              POL-CONFLICT-01
            </span>
          </div>
          <p className="text-amber-800 mt-1 leading-relaxed">
            Both <strong>v2.0</strong> and <strong>v3.0</strong> of the Refund Policy are indexed in the vector store. The ResolveOps Policy Gateway deterministically flags citations citing deprecated documents and enforces the latest active version (v3.0) with strict authority tiers.
          </p>
        </div>
      </div>

      {/* Main Grid: Document List + Viewer / Editor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Document List (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search policy corpus..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-white placeholder-slate-400 focus:outline-hidden focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-1 flex items-center justify-between">
            <span>Policy Documents ({filteredPolicies.length})</span>
            {loading && <span className="text-[10px] text-blue-600 animate-pulse font-normal">Loading...</span>}
          </div>

          <div className="space-y-2 max-h-[620px] overflow-y-auto pr-1">
            {filteredPolicies.map((doc) => {
              const isSelected = selectedPolicy?.id === doc.id;
              return (
                <div
                  key={doc.id}
                  onClick={() => fetchPolicyDetail(doc.id)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? "bg-white border-blue-500 shadow-xs ring-1 ring-blue-500/20"
                      : "bg-white border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded ${
                        doc.status === "active"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : "bg-slate-100 text-slate-500 border border-slate-200"
                      }`}
                    >
                      {doc.status.toUpperCase()} ({doc.version})
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {(doc.size_bytes / 1024).toFixed(1)} KB
                    </span>
                  </div>
                  <h3 className="text-xs font-bold text-slate-900 line-clamp-1">
                    {doc.name}
                  </h3>
                  <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2 leading-relaxed">
                    {doc.snippet || doc.filename}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Document Viewer / Editor (8 cols) */}
        <div className="lg:col-span-8 bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between min-h-[500px]">
          {isEditing || isCreating ? (
            /* Editing / Creating Mode */
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 rounded-lg bg-blue-100 text-blue-700">
                    <Edit3 className="w-4 h-4" />
                  </span>
                  <h2 className="text-sm font-bold text-slate-900">
                    {isCreating ? "Create New Policy Document" : `Editing: ${selectedPolicy?.filename}`}
                  </h2>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setIsEditing(false);
                      setIsCreating(false);
                    }}
                    className="px-2.5 py-1 text-xs border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={isCreating ? saveCreate : saveEdit}
                    disabled={saving}
                    className="px-3.5 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold flex items-center gap-1.5 shadow-xs disabled:opacity-50 cursor-pointer"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{saving ? "Indexing..." : "Save & Re-Index"}</span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase">Policy Title</label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    placeholder="e.g. VIP Escalation Rules"
                    className="w-full mt-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase">Version</label>
                  <input
                    type="text"
                    value={editVersion}
                    onChange={(e) => setEditVersion(e.target.value)}
                    placeholder="e.g. v3.2"
                    className="w-full mt-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase">Status</label>
                  <select
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value as any)}
                    className="w-full mt-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200"
                  >
                    <option value="active">active (Authoritative)</option>
                    <option value="deprecated">deprecated (Legacy)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-500 uppercase">
                  Markdown Content & Rules
                </label>
                <textarea
                  rows={16}
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full mt-1 p-3 text-xs font-mono rounded-lg border border-slate-200 focus:outline-hidden focus:ring-1 focus:ring-blue-500 bg-slate-50/50 leading-relaxed"
                  placeholder="Enter markdown policy content..."
                />
              </div>
            </div>
          ) : selectedPolicy ? (
            /* Document Viewing Mode */
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-slate-200 mb-6">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-slate-900">
                      {selectedPolicy.name}
                    </h2>
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
                      {selectedPolicy.version}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Filename: <code className="font-mono text-[11px]">{selectedPolicy.filename}</code> · Size: {(selectedPolicy.size_bytes / 1024).toFixed(1)} KB
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={startEdit}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-700 flex items-center gap-1.5 shadow-2xs cursor-pointer"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>Edit Markdown</span>
                  </button>

                  {selectedPolicy.status === "active" ? (
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
              </div>

              <div className="prose prose-slate max-w-none text-xs leading-relaxed whitespace-pre-wrap font-sans text-slate-800 bg-slate-50/40 p-4 rounded-lg border border-slate-100">
                {selectedPolicy.content || selectedPolicy.snippet}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-slate-400 text-xs">
              Select a policy document to view or edit
            </div>
          )}

          <div className="mt-8 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="font-mono text-[11px]">
              Qdrant Collection: <code>resolveops_policies</code> (Cosine Metric)
            </span>
            <span className="text-blue-600 font-medium">FastEmbed BAAI/bge-small-en-v1.5 · BM25 Lexical · FlashRank</span>
          </div>
        </div>
      </div>
    </div>
  );
}
