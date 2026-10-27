"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ServiceHealth } from "./types";

interface AppContextType {
  /** True while the backend's global kill switch is engaged. */
  killSwitch: boolean;
  /** Dependency status reported by the backend's /ready endpoint (empty until loaded). */
  systemHealth: ServiceHealth[];
  /** False when the backend could not be reached on the last poll. */
  backendReachable: boolean;
  /** Set the backend kill switch. Resolves with an error message on failure, otherwise null. */
  toggleKillSwitch: (enabled: boolean) => Promise<string | null>;
  refresh: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const POLL_MS = 10000;

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [killSwitch, setKillSwitch] = useState<boolean>(false);
  const [systemHealth, setSystemHealth] = useState<ServiceHealth[]>([]);
  const [backendReachable, setBackendReachable] = useState<boolean>(true);

  const refresh = useCallback(async () => {
    try {
      const ks = await fetch("/api/admin/kill-switch", { cache: "no-store" });
      if (ks.ok) setKillSwitch(Boolean((await ks.json()).active));

      // /ready answers 503 when the database is down but still returns the dependency report.
      const ready = await fetch("/ready", { cache: "no-store" });
      const body = await ready.json();
      const checkedAt = new Date().toISOString();
      const deps = (body.dependencies ?? {}) as Record<
        string,
        { status: string; latency_ms?: number | null }
      >;
      setSystemHealth(
        Object.entries(deps).map(([name, d]) => ({
          name,
          status: d.status === "ok" ? "healthy" : "unreachable",
          latency_ms: d.latency_ms ?? null,
          last_check: checkedAt,
        }))
      );
      setBackendReachable(true);
    } catch {
      setBackendReachable(false);
      setSystemHealth([]);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const toggleKillSwitch = useCallback(async (enabled: boolean): Promise<string | null> => {
    try {
      const res = await fetch("/api/admin/kill-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: enabled }),
      });
      if (!res.ok) return `Kill switch update failed (${res.status})`;
      setKillSwitch(Boolean((await res.json()).active));
      return null;
    } catch {
      return "Backend unreachable";
    }
  }, []);

  return (
    <AppContext.Provider value={{ killSwitch, systemHealth, backendReachable, toggleKillSwitch, refresh }}>
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
