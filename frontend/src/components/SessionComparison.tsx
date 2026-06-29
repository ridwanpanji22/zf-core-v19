"use client";

import { useState, useEffect } from "react";
import { useWebSocket } from "@/lib/ws";
import { SessionComparison } from "@/lib/types";

export default function SessionComparisonComponent() {
  const [comparisons, setComparisons] = useState<SessionComparison[]>([]);
  const update = useWebSocket<SessionComparison[]>("session_comparison");

  useEffect(() => {
    if (update) {
      // Filter absolute delta changes > 0.05 only
      const filtered = update.filter(c => Math.abs(c.delta) > 0.05);
      setComparisons(filtered.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta)));
    }
  }, [update]);

  if (comparisons.length === 0) {
    return (
      <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6 text-center text-slate-400 text-sm">
        Tidak ada transisi ZF-Score signifikan (&gt; 0.05) terdeteksi sesi ini.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6 space-y-4">
      <h2 className="text-base font-bold text-white">
        Transisi Fase Aset (Komparasi Sesi)
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-xs text-slate-300">
          <thead className="border-b border-[#1E293B] text-slate-400 font-bold uppercase tracking-wider">
            <tr>
              <th className="pb-2">Aset</th>
              <th className="pb-2 text-right">Sesi Sblm</th>
              <th className="pb-2 text-right">Sesi Kini</th>
              <th className="pb-2 text-right">Delta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E293B]/50">
            {comparisons.map((c) => (
              <tr key={c.symbol} className="hover:bg-[#1E293B]/20">
                <td className="py-2.5 font-semibold text-white">{c.symbol.split("-")[0]}</td>
                <td className="py-2.5 text-right text-slate-400">{c.zf_score_prev.toFixed(4)}</td>
                <td className="py-2.5 text-right">{c.zf_score_curr.toFixed(4)}</td>
                <td className={`py-2.5 text-right font-bold flex items-center justify-end gap-1 ${
                  c.transition === "worsening" ? "text-red-400" : "text-emerald-400"
                }`}>
                  {c.transition === "worsening" ? "↑" : "↓"} {c.delta > 0 ? "+" : ""}{c.delta.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
