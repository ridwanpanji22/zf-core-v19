"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useWebSocket } from "@/lib/ws";
import { apiFetch } from "@/lib/api";
import { AssetDetail, DemoWallet, DemoPosition } from "@/lib/types";
import DepthChart from "@/components/DepthChart";
import LiquidationHeatmap from "@/components/LiquidationHeatmap";
import FundingRateChart from "@/components/FundingRateChart";

interface PageProps {
  params: Promise<{ symbol: string }>;
}

export default function AssetDetailPage({ params }: PageProps) {
  const router = useRouter();
  const { symbol } = use(params);

  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"depth" | "heatmap">("depth");

  // Trade form state
  const [side, setSide] = useState<"long" | "short">("long");
  const [sizeUsdt, setSizeUsdt] = useState<number>(1000);
  const [leverage, setLeverage] = useState<number>(5);
  const [submitting, setSubmitting] = useState(false);
  const [wallet, setWallet] = useState<DemoWallet | null>(null);

  // Initial Fetch metadata
  useEffect(() => {
    const loadData = async () => {
      const [assetRes, walletRes] = await Promise.all([
        apiFetch<AssetDetail>(`/api/assets/${symbol}`),
        apiFetch<DemoWallet>("/api/demo/wallet"),
      ]);

      if (assetRes.success && assetRes.data) {
        setAsset(assetRes.data);
      } else {
        router.push("/dashboard");
      }

      if (walletRes.success && walletRes.data) {
        setWallet(walletRes.data);
      }
      setLoading(false);
    };
    loadData();
  }, [symbol, router]);

  // Real-time metadata updates via WebSocket
  const liveUpdate = useWebSocket<AssetDetail>("asset_update");
  useEffect(() => {
    if (liveUpdate && liveUpdate.symbol === symbol) {
      setAsset((prev) => (prev ? { ...prev, ...liveUpdate } : null));
    }
  }, [liveUpdate, symbol]);

  const handleOpenTrade = async () => {
    setSubmitting(true);
    try {
      const res = await apiFetch<DemoPosition>("/api/demo/positions", {
        method: "POST",
        body: JSON.stringify({
          symbol,
          side,
          size_usdt: sizeUsdt,
          leverage,
        }),
      });

      if (res.success) {
        alert(`Virtual ${side.toUpperCase()} posisi berhasil dibuka untuk ${symbol}!`);
        // Refresh wallet balance
        const wRes = await apiFetch<DemoWallet>("/api/demo/wallet");
        if (wRes.success && wRes.data) {
          setWallet(wRes.data);
        }
      } else {
        alert(res.error?.message || "Gagal membuka posisi virtual.");
      }
    } catch (e: any) {
      alert(e.message || "Gagal membuka posisi virtual.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-white">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#00FF88] border-t-transparent" />
      </div>
    );
  }

  if (!asset) return null;

  return (
    <div className="space-y-8">
      {/* Header Info */}
      <div className="flex flex-col justify-between gap-4 border-b border-[#1E293B] pb-6 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            {asset.symbol}
          </h1>
          <p className="text-sm text-slate-400">
            Fase: <span className="font-bold uppercase text-[#00FF88]">{asset.status.replace("_", " ")}</span> ({asset.mode === "deep_analysis" ? "Deep Analysis" : "Heartbeat"})
          </p>
        </div>
        <div className="flex flex-wrap gap-6 text-sm">
          <div className="rounded border border-[#1E293B] bg-[#0F172A] p-3 text-center">
            <span className="block text-xs text-slate-400">Harga Terakhir</span>
            <span className="text-lg font-bold text-white">${asset.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
          <div className="rounded border border-[#1E293B] bg-[#0F172A] p-3 text-center">
            <span className="block text-xs text-slate-400">ZF-Score</span>
            <span className="text-lg font-bold text-yellow-400">{asset.zf_score.toFixed(4)}</span>
          </div>
          <div className="rounded border border-[#1E293B] bg-[#0F172A] p-3 text-center">
            <span className="block text-xs text-slate-400">Ψ_total</span>
            <span className="text-lg font-bold text-purple-400">{asset.psi_total.toFixed(4)}</span>
          </div>
          <div className="rounded border border-[#1E293B] bg-[#0F172A] p-3 text-center">
            <span className="block text-xs text-slate-400">D_res</span>
            <span className="text-lg font-bold text-[#00FF88]">{asset.d_res.toFixed(2)}%</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Left Side: Chart components */}
        <div className="lg:col-span-2 space-y-8">
          <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6">
            <div className="mb-6 flex border-b border-[#1E293B]">
              <button
                onClick={() => setActiveTab("depth")}
                className={`pb-3 text-sm font-semibold transition-all duration-150 ${
                  activeTab === "depth"
                    ? "border-b-2 border-[#00FF88] text-[#00FF88]"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Kedalaman Pasar (Depth Chart)
              </button>
              <button
                onClick={() => setActiveTab("heatmap")}
                className={`ml-6 pb-3 text-sm font-semibold transition-all duration-150 ${
                  activeTab === "heatmap"
                    ? "border-b-2 border-[#00FF88] text-[#00FF88]"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Kerapatan Likuidasi
              </button>
            </div>
            {activeTab === "depth" ? (
              <DepthChart symbol={symbol} />
            ) : (
              <LiquidationHeatmap symbol={symbol} />
            )}
          </div>

          <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6 space-y-4">
            <h2 className="text-sm font-bold text-white">Funding Rate History (7 hari)</h2>
            <FundingRateChart symbol={symbol} />
          </div>
        </div>

        {/* Right Side: Demo paper execution form */}
        <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6 space-y-6">
          <h2 className="text-lg font-bold text-white">Eksekusi Virtual (Mode Demo)</h2>

          {wallet && (
            <div className="rounded bg-[#1E293B]/50 p-3 text-xs flex justify-between text-slate-300">
              <span>Saldo Tersedia:</span>
              <span className="font-bold text-white">${wallet.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })} USDT</span>
            </div>
          )}

          {/* Trade Direction selection */}
          <div className="flex gap-2">
            <button
              onClick={() => setSide("long")}
              className={`flex-1 rounded py-2.5 text-xs font-bold transition-all duration-150 ${
                side === "long" ? "bg-emerald-500 text-slate-950" : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              LONG
            </button>
            <button
              onClick={() => setSide("short")}
              className={`flex-1 rounded py-2.5 text-xs font-bold transition-all duration-150 ${
                side === "short" ? "bg-red-500 text-slate-950" : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              SHORT
            </button>
          </div>

          {/* Size USDT input */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-400">Order Size (USDT)</label>
            <input
              type="number"
              value={sizeUsdt}
              onChange={(e) => setSizeUsdt(Math.max(1, Number(e.target.value)))}
              className="w-full rounded-md border border-[#1E293B] bg-[#020617] px-4 py-2.5 text-sm text-white focus:border-[#00FF88] focus:outline-none"
            />
          </div>

          {/* Leverage slider */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-semibold text-slate-400">
              <label>Leverage</label>
              <span className="text-white">{leverage}x</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              value={leverage}
              onChange={(e) => setLeverage(Number(e.target.value))}
              className="w-full accent-[#00FF88]"
            />
            <span className="block text-[10px] text-slate-500">Maksimal leverage demo: 10x</span>
          </div>

          <div className="border-t border-[#1E293B] pt-4 space-y-2 text-xs text-slate-400">
            <div className="flex justify-between">
              <span>Estimasi Margin:</span>
              <span className="text-white">${(sizeUsdt / leverage).toFixed(2)} USDT</span>
            </div>
            <div className="flex justify-between">
              <span>Estimasi Fee (Taker 0.05%):</span>
              <span className="text-white">${(sizeUsdt * 0.0005).toFixed(2)} USDT</span>
            </div>
          </div>

          <button
            onClick={handleOpenTrade}
            disabled={submitting}
            className={`w-full rounded-md py-3 text-sm font-bold text-slate-950 transition-all duration-150 ${
              side === "long" ? "bg-emerald-400 hover:bg-emerald-300" : "bg-red-400 hover:bg-red-300"
            } disabled:opacity-50`}
          >
            {submitting ? "Memproses Order..." : `Buka ${side.toUpperCase()} Posisi`}
          </button>
        </div>
      </div>
    </div>
  );
}
