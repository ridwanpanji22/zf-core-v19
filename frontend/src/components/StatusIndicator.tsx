"use client";

import { useWebSocket } from "@/lib/ws";
import { SystemStatus } from "@/lib/types";

export default function StatusIndicator() {
  const status = useWebSocket<SystemStatus>("system_status");

  const isCB = status?.circuit_breaker ?? false;
  const isCold = status?.cold_mode ?? false;

  return (
    <div className="flex items-center gap-4 text-xs font-semibold">
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
        </span>
        <span className="text-slate-300">System: Online</span>
      </div>

      {isCB && (
        <span className="animate-pulse rounded bg-red-500/20 px-2.5 py-1 text-red-400 border border-red-500/30">
          🚨 CIRCUIT BREAKER
        </span>
      )}

      {isCold && (
        <span className="rounded bg-blue-500/20 px-2.5 py-1 text-blue-400 border border-blue-500/30">
          ❄️ MODE DINGIN
        </span>
      )}
    </div>
  );
}
