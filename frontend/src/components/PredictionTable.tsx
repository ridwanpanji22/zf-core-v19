"use client";

import { useState, useEffect } from "react";
import { useWebSocket } from "@/lib/ws";
import { PredictionTop20 } from "@/lib/types";
import { apiFetch } from "@/lib/api";

export default function PredictionTable() {
  const [data, setData] = useState<PredictionTop20 | null>(null);

  useEffect(() => {
    const loadPredictions = async () => {
      const res = await apiFetch<PredictionTop20>("/api/predictions/top20");
      if (res.success && res.data) {
        setData(res.data);
      }
    };
    loadPredictions();
  }, []);

  const liveUpdate = useWebSocket<PredictionTop20>("prediction_update");
  useEffect(() => {
    if (liveUpdate) {
      setData(liveUpdate);
    }
  }, [liveUpdate]);

  if (!data) {
    return (
      <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6 text-center text-slate-400 text-sm">
        Memuat data prediksi...
      </div>
    );
  }

  const getHeaderColor = () => {
    if (data.market_direction === "up") return "text-emerald-400";
    if (data.market_direction === "down") return "text-red-400";
    return "text-slate-300";
  };

  return (
    <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6 space-y-4">
      <h2 className={`text-base font-bold tracking-tight ${getHeaderColor()}`}>
        {data.title}
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-xs text-slate-300">
          <thead className="border-b border-[#1E293B] text-slate-400 font-bold uppercase tracking-wider">
            <tr>
              <th className="pb-2 pr-2">#</th>
              <th className="pb-2 pr-2">Aset</th>
              <th className="pb-2 pr-2 text-right">Harga</th>
              <th className="pb-2 text-right">Proyeksi 10H</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E293B]/50">
            {data.assets.map((asset) => (
              <tr key={asset.symbol} className="hover:bg-[#1E293B]/20">
                <td className="py-2.5 pr-2 font-medium">{asset.rank}</td>
                <td className="py-2.5 pr-2 font-semibold text-white">{asset.symbol.split("-")[0]}</td>
                <td className="py-2.5 pr-2 text-right">${asset.price ? asset.price.toLocaleString(undefined, { minimumFractionDigits: 2 }) : "-"}</td>
                <td className={`py-2.5 text-right font-bold ${asset.predicted_change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {asset.predicted_change_pct >= 0 ? "+" : ""}{asset.predicted_change_pct.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
