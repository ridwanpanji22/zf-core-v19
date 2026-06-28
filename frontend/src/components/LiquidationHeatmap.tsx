"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface LiquidationPoint {
  price: number;
  volume: number;
  side: "buy" | "sell";
}

interface LiquidationHeatmapProps {
  symbol: string;
}

export default function LiquidationHeatmap({ symbol }: LiquidationHeatmapProps) {
  const [data, setData] = useState<LiquidationPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLiqMap = async () => {
      const res = await apiFetch<LiquidationPoint[]>(`/api/assets/${symbol}/liquidation-map`);
      if (res.success && res.data) {
        setData(res.data);
      }
      setLoading(false);
    };
    fetchLiqMap();
  }, [symbol]);

  if (loading) return <div className="text-sm text-slate-400">Loading Heatmap...</div>;
  if (!data.length) return <div className="text-sm text-slate-400">No liquidation clusters detected</div>;

  const maxVolume = Math.max(...data.map((d) => d.volume), 1);

  return (
    <div className="space-y-4">
      <h3 className="text-xs font-semibold text-slate-400">
        Estimasi Zona Kerapatan Likuidasi
      </h3>
      <div className="space-y-3">
        {data.map((point, index) => {
          const widthPct = Math.min((point.volume / maxVolume) * 100, 100);
          return (
            <div key={index} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className={point.side === "buy" ? "text-[#00FF88]" : "text-red-400"}>
                  {point.side === "buy" ? "Long Liq" : "Short Liq"} @ ${point.price.toLocaleString()}
                </span>
                <span className="text-slate-400">
                  Vol: ${point.volume.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
              <div className="h-2 w-full rounded bg-slate-800">
                <div
                  className={`h-full rounded transition-all duration-300 ${
                    point.side === "buy"
                      ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
                      : "bg-gradient-to-r from-red-500 to-red-400"
                  }`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
