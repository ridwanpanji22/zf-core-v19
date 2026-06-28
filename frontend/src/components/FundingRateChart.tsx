"use client";

import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { apiFetch } from "@/lib/api";

interface HistoryData {
  time: string;
  funding_rate: number | null;
}

interface FundingRateChartProps {
  symbol: string;
}

export default function FundingRateChart({ symbol }: FundingRateChartProps) {
  const [data, setData] = useState<HistoryData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      const res = await apiFetch<HistoryData[]>(`/api/assets/${symbol}/history?limit=30`);
      if (res.success && res.data) {
        setData(res.data);
      }
      setLoading(false);
    };
    fetchHistory();
  }, [symbol]);

  if (loading) return <div className="text-sm text-slate-400">Loading Funding Rate...</div>;

  // Filter items with valid funding rates
  const formattedData = data
    .filter((d) => d.funding_rate !== null)
    .map((d) => ({
      time: new Date(d.time).toLocaleDateString(undefined, { day: "numeric", month: "short" }),
      "Funding Rate": (d.funding_rate || 0) * 100, // percentage
    }));

  if (!formattedData.length) {
    return <div className="text-sm text-slate-400">No Funding Rate history available</div>;
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formattedData}>
          <XAxis dataKey="time" stroke="#475569" fontSize={9} tickLine={false} />
          <YAxis
            stroke="#475569"
            fontSize={9}
            tickLine={false}
            tickFormatter={(v) => `${v.toFixed(3)}%`}
            width={55}
          />
          <Tooltip
            contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b" }}
            labelStyle={{ color: "#fff" }}
            formatter={(val: number) => [`${val.toFixed(4)}%`, "Funding Rate"]}
          />
          <Line
            type="monotone"
            dataKey="Funding Rate"
            stroke="#3b82f6"
            strokeWidth={1.5}
            dot={{ r: 2, fill: "#3b82f6" }}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
