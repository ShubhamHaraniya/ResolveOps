"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Sparkles,
  X,
  Send,
  RotateCw,
  ExternalLink,
  BookOpen,
  Ticket as TicketIcon,
  Bot,
  User,
} from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  matched_tickets?: any[];
  citations?: any[];
  timestamp: string;
}

const DEFAULT_SUGGESTIONS = [
  "Find all tickets about refunds",
  "Which tickets are currently awaiting approval?",
  "What is our policy for refund threshold limits?",
  "Can an agent grant prod-admin access?",
  "Show tickets requested by sarah@acme.corp",
];

export function CopilotDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      role: "assistant",
      content:
        "Hello! I'm your **ResolveOps Copilot**, powered by dual-layer RAG. I can search tickets, customer accounts, pending approvals and the policy documents.\n\nAsk me anything or try one of the quick suggestions below!",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  // Global keyboard shortcut: Ctrl+K or Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSend = async (queryText?: string) => {
    const text = queryText || inputQuery;
    if (!text.trim() || loading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setLoading(true);

    try {
      const res = await fetch("/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: text,
          messages: messages.slice(-4).map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const assistantMsg: Message = {
          id: `ai-${Date.now()}`,
          role: "assistant",
          content: data.content,
          matched_tickets: data.matched_tickets || [],
          citations: data.citations || [],
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: "assistant",
            content: "Sorry, I encountered an issue retrieving operational data. Please try again.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: `Network error: ${err.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Helper to format markdown links and bolding in assistant text
  const renderMessageContent = (content: string) => {
    // Regex for markdown links [text](url)
    const parts = content.split(/(\[[^\]]+\]\([^)]+\))/g);
    return parts.map((part, index) => {
      const match = part.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (match) {
        const linkText = match[1].replace(/\*\*/g, "").trim();
        const linkUrl = match[2].trim();
        return (
          <Link
            key={index}
            href={linkUrl}
            onClick={() => {
              if (linkUrl.startsWith("/tickets/")) setIsOpen(false);
            }}
            className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:text-blue-800 underline bg-blue-50/80 px-1.5 py-0.5 rounded mx-0.5"
          >
            <span>{linkText}</span>
            <ExternalLink className="w-2.5 h-2.5" />
          </Link>
        );
      }
      
      // Render bold tokens **text**
      const subParts = part.split(/(\*\*[^*]+\*\*)/g);
      return (
        <span key={index}>
          {subParts.map((sp, sIdx) => {
            if (sp.startsWith("**") && sp.endsWith("**")) {
              return <strong key={sIdx} className="font-semibold text-slate-900">{sp.slice(2, -2)}</strong>;
            }
            return sp;
          })}
        </span>
      );
    });
  };

  return (
    <>
      {/* Floating Trigger Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-40 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-full p-3.5 shadow-xl flex items-center gap-2.5 transition-all transform hover:scale-105 cursor-pointer ring-4 ring-indigo-500/20"
          title="Open AI Copilot (Ctrl+K)"
        >
          <Sparkles className="w-5 h-5 text-amber-300 animate-pulse" />
          <span className="text-xs font-bold tracking-tight pr-1">AI Copilot</span>
          <span className="text-[10px] bg-white/20 px-1.5 py-0.5 rounded font-mono hidden sm:inline">
            ⌘K
          </span>
        </button>
      )}

      {/* Floating Chat Drawer */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-full max-w-md h-[620px] bg-white rounded-2xl border border-slate-200 shadow-2xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-5 duration-200">
          {/* Header */}
          <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-4 text-white flex items-center justify-between border-b border-indigo-900">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-indigo-500/20 text-amber-300 border border-indigo-500/30">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-bold text-xs flex items-center gap-1.5">
                  <span>ResolveOps AI Copilot</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/30 text-indigo-300 font-mono">
                    RAG LIVE
                  </span>
                </h3>
                <p className="text-[10px] text-slate-300">
                  Policy knowledge base & database ticket finder
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={() =>
                  setMessages([
                    {
                      id: `cleared-${Date.now()}`,
                      role: "assistant",
                      content: "Chat cleared. What can I help you find across tickets or policies?",
                      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                    },
                  ])
                }
                className="text-slate-400 hover:text-white p-1 rounded hover:bg-white/10 text-[11px] transition-colors cursor-pointer"
                title="Clear chat"
              >
                Clear
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3.5 bg-slate-50/50 text-xs">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "assistant" && (
                  <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                    <Bot className="w-3.5 h-3.5" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-2xl p-3 text-xs leading-relaxed shadow-2xs ${
                    m.role === "user"
                      ? "bg-blue-600 text-white rounded-br-xs"
                      : "bg-white text-slate-800 border border-slate-200 rounded-bl-xs"
                  }`}
                >
                  <div className="whitespace-pre-wrap font-sans">
                    {renderMessageContent(m.content)}
                  </div>

                  {/* Matched Tickets Quick Cards */}
                  {m.matched_tickets && m.matched_tickets.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-slate-100 space-y-1.5">
                      <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                        Direct Ticket Matches:
                      </span>
                      {m.matched_tickets.map((t: any) => (
                        <Link
                          key={t.id}
                          href={`/tickets/${t.id}`}
                          onClick={() => setIsOpen(false)}
                          className="flex items-center justify-between p-1.5 rounded-lg bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 transition-colors group"
                        >
                          <div className="flex items-center gap-1.5">
                            <TicketIcon className="w-3 h-3 text-blue-600" />
                            <span className="font-mono font-bold text-slate-900 group-hover:text-blue-700">
                              {t.number}
                            </span>
                            <span className="text-[11px] text-slate-600 truncate max-w-[150px]">
                              {t.subject}
                            </span>
                          </div>
                          <span className="text-[9px] px-1 rounded bg-slate-200 text-slate-700 uppercase font-mono">
                            {t.status}
                          </span>
                        </Link>
                      ))}
                    </div>
                  )}

                  {/* Policy Citations Badges */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="mt-2 pt-1.5 border-t border-slate-100 flex flex-wrap gap-1">
                      {m.citations.map((c: any, i: number) => (
                        <span
                          key={i}
                          className="inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-mono"
                        >
                          <BookOpen className="w-2.5 h-2.5" />
                          {c.id} {c.version}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="text-[9px] mt-1 opacity-60 text-right font-mono">
                    {m.timestamp}
                  </div>
                </div>

                {m.role === "user" && (
                  <div className="w-6 h-6 rounded-full bg-slate-700 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                    <User className="w-3.5 h-3.5" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-2.5 items-center text-slate-400 text-xs py-1">
                <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0">
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                </div>
                <span className="italic animate-pulse">Searching policies and database...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick suggestions when chat is young */}
          {messages.length <= 3 && (
            <div className="px-4 py-2 bg-slate-100/80 border-t border-slate-200/80 flex items-center gap-1.5 overflow-x-auto text-[10px]">
              <span className="text-slate-400 shrink-0 font-medium">Try:</span>
              {DEFAULT_SUGGESTIONS.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(s)}
                  className="px-2 py-0.5 rounded-full bg-white border border-slate-200 hover:border-blue-400 hover:bg-blue-50 text-slate-700 shrink-0 transition-colors cursor-pointer"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input Footer */}
          <div className="p-3 border-t border-slate-200 bg-white">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2"
            >
              <div className="relative flex-1">
                <input
                  type="text"
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  placeholder="Ask policy rules, search tickets, check approvals..."
                  className="w-full text-xs pl-3 pr-8 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 bg-slate-50 placeholder-slate-400"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !inputQuery.trim()}
                className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white transition-colors cursor-pointer shadow-xs"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
