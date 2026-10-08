"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import {
  Ticket,
  ApprovalItem,
  AuditEvent,
  TraceRun,
  ServiceHealth,
  DemoScenario,
} from "./types";
import {
  MOCK_TICKETS,
  MOCK_APPROVALS,
  MOCK_AUDIT_LOG,
  MOCK_TRACE_RUNS,
  MOCK_SYSTEM_HEALTH,
  MOCK_DEMO_SCENARIOS,
} from "./mockData";

interface AppContextType {
  tickets: Ticket[];
  approvals: ApprovalItem[];
  auditLog: AuditEvent[];
  systemHealth: ServiceHealth[];
  killSwitch: boolean;
  demoBannerVisible: boolean;
  dismissDemoBanner: () => void;
  toggleKillSwitch: (enabled: boolean) => void;
  approveAction: (approvalId: string, editedArgs?: Record<string, any>) => void;
  rejectAction: (approvalId: string, reason: string) => void;
  runScenario: (scenarioId: string) => Ticket | null;
  getTicketById: (ticketId: string) => Ticket | undefined;
  getTraceRun: (runId: string) => TraceRun | undefined;
  resetDemoData: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [tickets, setTickets] = useState<Ticket[]>(MOCK_TICKETS);
  const [approvals, setApprovals] = useState<ApprovalItem[]>(MOCK_APPROVALS);
  const [auditLog, setAuditLog] = useState<AuditEvent[]>(MOCK_AUDIT_LOG);
  const [systemHealth, setSystemHealth] = useState<ServiceHealth[]>(MOCK_SYSTEM_HEALTH);
  const [killSwitch, setKillSwitch] = useState<boolean>(false);
  const [demoBannerVisible, setDemoBannerVisible] = useState<boolean>(true);

  const dismissDemoBanner = () => setDemoBannerVisible(false);

  const toggleKillSwitch = (enabled: boolean) => {
    setKillSwitch(enabled);
    const newEvent: AuditEvent = {
      id: `aud-kill-${Date.now()}`,
      timestamp: new Date().toISOString(),
      run_id: "system-control",
      ticket_id: "global",
      actor_type: "human",
      actor_id: "sec_admin_01",
      event: enabled ? "global_kill_switch_activated" : "global_kill_switch_deactivated",
      result_status: enabled ? "BLOCKED" : "SUCCESS",
      prev_hash: auditLog[0]?.row_hash || "0000000000000000000000000000000000000000000000000000000000000000",
      row_hash: Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
      args_redacted: { kill_switch_active: enabled },
    };
    setAuditLog((prev) => [newEvent, ...prev]);
  };

  const approveAction = (approvalId: string, editedArgs?: Record<string, any>) => {
    const item = approvals.find((a) => a.id === approvalId);
    if (!item) return;

    // Check kill switch
    if (killSwitch) {
      alert("GLOBAL KILL SWITCH IS ACTIVE: Execution blocked by security policy gateway.");
      return;
    }

    // Remove from pending approvals
    setApprovals((prev) => prev.filter((a) => a.id !== approvalId));

    // Update ticket state
    setTickets((prev) =>
      prev.map((t) => {
        if (t.id === item.ticket_id) {
          return {
            ...t,
            status: "resolved",
            proposed_action: t.proposed_action
              ? {
                  ...t.proposed_action,
                  status: "executed",
                  arguments: editedArgs || t.proposed_action.arguments,
                  execution_result: {
                    status: "SUCCESS",
                    timestamp: new Date().toISOString(),
                    transaction_id: `tx_${Math.random().toString(36).substring(2, 10)}`,
                    gateway_verified: true,
                    readback_status: "MATCH_CONFIRMED",
                  },
                }
              : undefined,
            messages: [
              ...t.messages,
              {
                id: `m-exec-${Date.now()}`,
                sender_type: "system",
                sender_name: "ResolveOps Policy Gateway",
                body: `Action approved by human reviewer. Gateway executed ${item.tool} with cryptographic hash validation (${item.args_hash.substring(0, 12)}...). Read-back verification confirmed state consistency. Ticket marked RESOLVED.`,
                timestamp: new Date().toISOString(),
              },
            ],
          };
        }
        return t;
      })
    );

    // Append to audit log
    const auditExecution: AuditEvent = {
      id: `aud-${Date.now()}`,
      timestamp: new Date().toISOString(),
      run_id: item.ticket_id,
      ticket_id: item.ticket_id,
      actor_type: "gateway",
      actor_id: "policy_gateway_v1",
      event: "action_executed",
      tool: item.tool,
      args_hash: item.args_hash,
      policy_rule: item.policy_rule,
      idempotency_key: `idem-${item.args_hash.substring(0, 16)}`,
      result_status: "SUCCESS",
      args_redacted: editedArgs || item.args,
      prev_hash: auditLog[0]?.row_hash || "0000000000000000000000000000000000000000000000000000000000000000",
      row_hash: Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
    };

    setAuditLog((prev) => [auditExecution, ...prev]);
  };

  const rejectAction = (approvalId: string, reason: string) => {
    const item = approvals.find((a) => a.id === approvalId);
    if (!item) return;

    setApprovals((prev) => prev.filter((a) => a.id !== approvalId));

    setTickets((prev) =>
      prev.map((t) => {
        if (t.id === item.ticket_id) {
          return {
            ...t,
            status: "blocked",
            proposed_action: t.proposed_action
              ? {
                  ...t.proposed_action,
                  status: "rejected",
                }
              : undefined,
            messages: [
              ...t.messages,
              {
                id: `m-rej-${Date.now()}`,
                sender_type: "agent",
                sender_name: "Reviewer Feedback",
                body: `Action rejected by human reviewer. Reason: "${reason}". Action was NOT executed.`,
                timestamp: new Date().toISOString(),
              },
            ],
          };
        }
        return t;
      })
    );

    const auditRejection: AuditEvent = {
      id: `aud-rej-${Date.now()}`,
      timestamp: new Date().toISOString(),
      run_id: item.ticket_id,
      ticket_id: item.ticket_id,
      actor_type: "human",
      actor_id: "reviewer_agent_01",
      event: "approval_rejected",
      tool: item.tool,
      args_hash: item.args_hash,
      policy_rule: item.policy_rule,
      result_status: "BLOCKED",
      args_redacted: { reason },
      prev_hash: auditLog[0]?.row_hash || "0000000000000000000000000000000000000000000000000000000000000000",
      row_hash: Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
    };

    setAuditLog((prev) => [auditRejection, ...prev]);
  };

  const runScenario = (scenarioId: string): Ticket | null => {
    const found = MOCK_DEMO_SCENARIOS.find((s) => s.id === scenarioId);
    if (!found) return null;
    const targetTicket = tickets.find((t) => t.id === found.ticket_id);
    return targetTicket || null;
  };

  const getTicketById = (ticketId: string) => {
    return tickets.find((t) => t.id === ticketId || t.ticket_number.toLowerCase() === ticketId.toLowerCase());
  };

  const getTraceRun = (runId: string) => {
    return MOCK_TRACE_RUNS[runId] || MOCK_TRACE_RUNS["run-9801-refund"];
  };

  const resetDemoData = () => {
    setTickets(MOCK_TICKETS);
    setApprovals(MOCK_APPROVALS);
    setAuditLog(MOCK_AUDIT_LOG);
    setKillSwitch(false);
  };

  return (
    <AppContext.Provider
      value={{
        tickets,
        approvals,
        auditLog,
        systemHealth,
        killSwitch,
        demoBannerVisible,
        dismissDemoBanner,
        toggleKillSwitch,
        approveAction,
        rejectAction,
        runScenario,
        getTicketById,
        getTraceRun,
        resetDemoData,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
