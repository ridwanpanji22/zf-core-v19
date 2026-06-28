"use client";

import { useEffect, useState } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { apiFetch } from "@/lib/api";
import { OrderBookData } from "@/lib/types";

interface DepthChartProps {
  symbol: string;
}

export default function DepthChart({ symbol }: DepthChartProps) {
  const [data, setData] = useState<OrderBookData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOrderBook = async () => {
      const res = await apiFetch<OrderBookData>(`/api/assets/${symbol}/orderbook`);
      if (res.success && res.data) {
        setData(res.data);
      }
      setLoading(false);
    };
    fetchOrderBook();
  }, [symbol]);

  if (loading) return <div className="text-sm text-slate-400">Loading Depth Chart...</div>;
  if (!data || (!data.bids.length && !data.asks.length)) {
    return <div className="text-sm text-slate-400">No Depth Data available</div>;
  }

  // Format bids and asks for mirrored recharts
  // bids: [price, size], asks: [price, size]
  // We want a combined dataset sorted by price.
  // Mirrored: left side is bids (green), right side is asks (red).
  const bidsFormatted = data.bids.map((b) => ({
    price: b[0],
    Bid: b[1],
    Ask: null,
  })).reverse(); // lowest bids to highest bids

  const asksFormatted = data.asks.map((a) => ({
    price: a[0],
    Bid: null,
    Ask: a[1],
  }));

  const chartData = [...bidsFormatted, ...asksFormatted];

  return (
    <div className="h-64 w-full">
      <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
        <span>Bids (Hijau)</span>
        <span>Rasio Kedalaman Bid: {data.bid_depth_ratio}</span>
        <span>Asks (Merah)</span>
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <XAxis
            dataKey="price"
            stroke="#475569"
            fontSize={10}
            tickLine={false}
          />
          <YAxis stroke="#475569" fontSize={10} tickLine={false} width={40} />
          <Tooltip
            contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b" }}
            labelStyle={{ color: "#fff" }}
          />
          <Area
            type="monotone"
            dataKey="Bid"
            stroke="#00ff88"
            fill="#00ff88"
            fillOpacity={0.2}
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="Ask"
            stroke="#ef4444"
            fill="#ef4444"
            fillOpacity={0.2}
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
