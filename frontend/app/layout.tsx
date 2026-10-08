import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { AppProvider } from "@/lib/store";
import { Sidebar } from "@/components/Sidebar";
import { TopNav } from "@/components/TopNav";
import { DemoBanner, KillSwitchBanner } from "@/components/DemoBanner";

export const metadata: Metadata = {
  title: "ResolveOps — Governed AI Support Operations",
  description:
    "Production-style governed AI platform for Northwind Cloud: LangGraph workflows, deterministic policy gateway, human-in-the-loop approvals, and audit log.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <body className="h-full bg-slate-50 text-slate-900 flex overflow-hidden" suppressHydrationWarning>
        <AppProvider>
          {/* Fixed Dark Navy Sidebar */}
          <Suspense fallback={<aside className="w-64 bg-[#0b1329] h-screen" />}>
            <Sidebar />
          </Suspense>

          {/* Right Main Content Area */}
          <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
            <Suspense fallback={null}>
              <DemoBanner />
            </Suspense>
            <Suspense fallback={null}>
              <KillSwitchBanner />
            </Suspense>
            <Suspense fallback={<div className="h-14 bg-white border-b border-slate-200" />}>
              <TopNav />
            </Suspense>

            {/* Scrollable page canvas */}
            <main className="flex-1 overflow-y-auto bg-slate-50">
              <Suspense fallback={<div className="p-8 text-xs text-slate-400">Loading...</div>}>
                {children}
              </Suspense>
            </main>
          </div>
        </AppProvider>
      </body>
    </html>
  );
}
