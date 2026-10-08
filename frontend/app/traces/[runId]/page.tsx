import { Suspense } from "react";
import TracesPage from "../page";

export default function TraceDetailRoute() {
  return (
    <Suspense fallback={<div className="p-8 text-xs text-slate-400">Loading trace...</div>}>
      <TracesPage />
    </Suspense>
  );
}
