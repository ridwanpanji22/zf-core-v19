"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useWebSocket } from "@/lib/ws";
import { Asset } from "@/lib/types";
import { apiFetch } from "@/lib/api";

export default function AssetTable() {
  const router = useRouter();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterMode, setFilterMode] = useState("all");
  const [sortField, setSortField] = useState<keyof Asset>("zf_score");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    const loadAssets = async () => {
      const res = await apiFetch<Asset[]>("/api/assets");
      if (res.success && res.data) {
        setAssets(res.data);
      }
    };
    loadAssets();
    // ponytail: poll every 10s as fallback while OLS WS proxy is broken
    // upgrade path: remove interval once WS works (Nginx or direct port)
    const interval = setInterval(loadAssets, 10_000);
    return () => clearInterval(interval);
  }, []);

  const liveUpdate = useWebSocket<Asset>("asset_update");
  useEffect(() => {
    if (liveUpdate) {
      setAssets((prev) => {
        const idx = prev.findIndex((a) => a.symbol === liveUpdate.symbol);
        if (idx !== -1) {
          const updated = [...prev];
          updated[idx] = { ...updated[idx], ...liveUpdate };
          return updated;
        } else {
          return [...prev, liveUpdate];
        }
      });
    }
  }, [liveUpdate]);

  const handleSort = (field: keyof Asset) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const processedAssets = assets
    .filter((a) => {
      const matchesSearch = a.symbol.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = filterStatus === "all" || a.status === filterStatus;
      const matchesMode = filterMode === "all" || a.mode === filterMode;
      return matchesSearch && matchesStatus && matchesMode;
    })
    .sort((a, b) => {
      const valA = a[sortField] ?? 0;
      const valB = b[sortField] ?? 0;
      if (typeof valA === "string" && typeof valB === "string") {
        return sortOrder === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      return sortOrder === "asc"
        ? (valA as number) - (valB as number)
        : (valB as number) - (valA as number);
    });

  const getZfScoreBg = (score: number) => {
    if (score < 0.5) return "text-emerald-400 font-bold";
    if (score < 0.8) return "text-slate-200";
    if (score < 0.85) return "text-yellow-400 font-bold animate-pulse";
    if (score < 0.99) return "text-red-500 font-bold animate-pulse";
    return "text-red-600 font-extrabold bg-red-950/20 px-2 py-0.5 rounded border border-red-500/50 animate-bounce";
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <input
          type="text"
          placeholder="Cari aset... (e.g. BTC)"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Cari aset berdasarkan simbol"
          className="w-full max-w-xs rounded-md border border-[#1E293B] bg-[#0F172A] px-4 py-2 text-sm text-white focus:border-[#00FF88] focus:outline-none focus:ring-1 focus:ring-[#00FF88]"
        />
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            aria-label="Filter berdasarkan status aset"
            className="rounded-md border border-[#1E293B] bg-[#0F172A] px-3 py-2 text-xs text-white focus:border-[#00FF88] focus:outline-none focus:ring-1 focus:ring-[#00FF88]"
          >
            <option value="all">Semua Status</option>
            <option value="normal">Normal</option>
            <option value="waspada">Waspada</option>
            <option value="code_red">Code Red</option>
          </select>
          <select
            value={filterMode}
            onChange={(e) => setFilterMode(e.target.value)}
            aria-label="Filter berdasarkan mode analisis"
            className="rounded-md border border-[#1E293B] bg-[#0F172A] px-3 py-2 text-xs text-white focus:border-[#00FF88] focus:outline-none focus:ring-1 focus:ring-[#00FF88]"
          >
            <option value="all">Semua Mode</option>
            <option value="heartbeat">Heartbeat</option>
            <option value="deep_analysis">Deep Analysis</option>
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-[#1E293B] bg-[#0F172A]">
        <table
          className="w-full border-collapse text-left text-sm text-slate-300"
          role="grid"
          aria-label="Tabel 200 Aset Kripto — ZF-Score & Structural Tension"
        >
          <thead className="bg-[#1E293B]/50 text-xs font-bold uppercase tracking-wider text-slate-400">
            <tr className="border-b border-[#1E293B]">
              <th className="px-6 py-4" scope="col">#</th>
              <th className="cursor-pointer px-6 py-4 hover:text-white" scope="col" onClick={() => handleSort("symbol")} aria-sort={sortField === "symbol" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>Aset</th>
              <th className="cursor-pointer px-6 py-4 hover:text-white" scope="col" onClick={() => handleSort("price")} aria-sort={sortField === "price" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>Harga</th>
              <th className="cursor-pointer px-6 py-4 hover:text-white" scope="col" onClick={() => handleSort("delta_24h")} aria-sort={sortField === "delta_24h" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>Δ 24h</th>
              <th className="cursor-pointer px-6 py-4 hover:text-white text-[#00FF88]" scope="col" onClick={() => handleSort("zf_score")} aria-sort={sortField === "zf_score" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>ZF-Score</th>
              <th className="cursor-pointer px-6 py-4 hover:text-white" scope="col" onClick={() => handleSort("psi_total")} aria-sort={sortField === "psi_total" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>Ψ_total</th>
              <th className="cursor-pointer px-6 py-4 hover:text-white" scope="col" onClick={() => handleSort("d_res")} aria-sort={sortField === "d_res" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>D_res</th>
              <th className="px-6 py-4" scope="col">Mode</th>
              <th className="px-6 py-4" scope="col">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E293B] bg-[#0F172A]/50">
            {processedAssets.map((asset, index) => (
              <tr
                key={asset.symbol}
                onClick={() => router.push(`/${asset.symbol}`)}
                onKeyDown={(e) => e.key === "Enter" && router.push(`/${asset.symbol}`)}
                tabIndex={0}
                role="row"
                aria-label={`${asset.symbol} — ZF-Score ${asset.zf_score.toFixed(4)}, Status ${asset.status}`}
                className="cursor-pointer border-b border-[#1E293B] transition-colors duration-150 hover:bg-[#1E293B]/30 focus:outline-none focus:bg-[#1E293B]/50 focus:ring-1 focus:ring-inset focus:ring-[#00FF88]/50"
              >
                <td className="px-6 py-4 font-medium">{index + 1}</td>
                <td className="px-6 py-4 font-bold text-white">{asset.symbol}</td>
                <td className="px-6 py-4">{asset.price ? `$${asset.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}` : "-"}</td>
                <td className={`px-6 py-4 font-medium ${asset.delta_24h >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {asset.delta_24h >= 0 ? "+" : ""}{asset.delta_24h ? `${asset.delta_24h.toFixed(2)}%` : "0.00%"}
                </td>
                <td className={`px-6 py-4 ${getZfScoreBg(asset.zf_score)}`}>{asset.zf_score.toFixed(4)}</td>
                <td className="px-6 py-4">{asset.psi_total.toFixed(4)}</td>
                <td className="px-6 py-4">{asset.d_res.toFixed(2)}%</td>
                <td className="px-6 py-4">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${asset.mode === "deep_analysis" ? "bg-purple-500/10 text-purple-400 border border-purple-500/20" : "bg-blue-500/10 text-blue-400 border border-blue-500/20"}`}>
                    {asset.mode === "deep_analysis" ? "Deep" : "Heartbeat"}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`rounded px-1.5 py-0.5 text-xs font-bold uppercase ${
                    asset.status === "normal" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                    asset.status === "waspada" ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20" :
                    "bg-red-500/10 text-red-400 border border-red-500/20"
                  }`}>
                    {asset.status.replace("_", " ")}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
