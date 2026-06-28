"use client";

import { useEffect, useState } from "react";
import { useWebSocket } from "@/lib/ws";
import { apiFetch } from "@/lib/api";
import { DemoWallet, DemoPosition, Asset } from "@/lib/types";

export default function DemoPanel() {
  const [wallet, setWallet] = useState<DemoWallet | null>(null);
  const [positions, setPositions] = useState<DemoPosition[]>([]);
  const [history, setHistory] = useState<DemoPosition[]>([]);
  const [activeTab, setActiveTab] = useState<"open" | "history">("open");

  const [assetsList, setAssetsList] = useState<Asset[]>([]);
  const [symbol, setSymbol] = useState("");
  const [side, setSide] = useState<"long" | "short">("long");
  const [sizeUsdt, setSizeUsdt] = useState(1000);
  const [leverage, setLeverage] = useState(5);
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    const [wRes, pRes, hRes, aRes] = await Promise.all([
      apiFetch<DemoWallet>("/api/demo/wallet"),
      apiFetch<DemoPosition[]>("/api/demo/positions"),
      apiFetch<DemoPosition[]>("/api/demo/history"),
      apiFetch<Asset[]>("/api/assets"),
    ]);

    if (wRes.success) setWallet(wRes.data);
    if (pRes.success && pRes.data) setPositions(pRes.data);
    if (hRes.success && hRes.data) setHistory(hRes.data);
    if (aRes.success && aRes.data) {
      setAssetsList(aRes.data);
      if (aRes.data.length > 0) setSymbol(aRes.data[0].symbol);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const liveUpdate = useWebSocket<Asset>("asset_update");
  useEffect(() => {
    if (liveUpdate && positions.length > 0) {
      setPositions((prev) =>
        prev.map((pos) => {
          if (pos.symbol === liveUpdate.symbol) {
            const price = liveUpdate.price;
            const entry = Number(pos.entry_price);
            const size = Number(pos.size_usdt);
            const pnl = pos.side === "long"
              ? ((price - entry) / entry) * size
              : ((entry - price) / entry) * size;
            return { ...pos, mark_price: price, unrealized_pnl: pnl };
          }
          return pos;
        })
      );
    }
  }, [liveUpdate, positions.length]);

  const handleOpen = async () => {
    if (!symbol) return;
    setSubmitting(true);
    const res = await apiFetch<DemoPosition>("/api/demo/positions", {
      method: "POST",
      body: JSON.stringify({ symbol, side, size_usdt: sizeUsdt, leverage }),
    });
    if (res.success) {
      await loadData();
    } else {
      alert(res.error?.message || "Gagal membuka posisi virtual");
    }
    setSubmitting(false);
  };

  const handleClose = async (id: number) => {
    const res = await apiFetch<DemoPosition>(`/api/demo/positions/${id}/close`, { method: "POST" });
    if (res.success) {
      await loadData();
    } else {
      alert(res.error?.message || "Gagal menutup posisi virtual");
    }
  };

  const handleReset = async () => {
    if (confirm("Apakah Anda yakin ingin me-reset wallet demo? Semua posisi akan ditutup dan saldo dikembalikan ke 10.000 USDT.")) {
      const res = await apiFetch<DemoWallet>("/api/demo/wallet/reset", { method: "POST" });
      if (res.success) {
        await loadData();
      }
    }
  };

  return (
    <div className="space-y-8">
      {wallet && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-lg border border-yellow-500/20 bg-[#0F172A] p-4 text-center shadow-lg">
            <span className="block text-xs font-semibold text-slate-400">Saldo Virtual</span>
            <span className="text-xl font-bold text-white">${wallet.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })} USDT</span>
          </div>
          <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-4 text-center shadow-lg">
            <span className="block text-xs font-semibold text-slate-400">Total Realized PnL</span>
            <span className={`text-xl font-bold ${wallet.total_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {wallet.total_pnl >= 0 ? "+" : ""}{wallet.total_pnl.toLocaleString(undefined, { minimumFractionDigits: 2 })} USDT
            </span>
          </div>
          <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-4 text-center shadow-lg">
            <span className="block text-xs font-semibold text-slate-400">Win Rate</span>
            <span className="text-xl font-bold text-white">{wallet.win_rate}% ({wallet.win_trades}/{wallet.total_trades})</span>
          </div>
          <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-4 text-center shadow-lg flex flex-col justify-between">
            <span className="block text-xs font-semibold text-slate-400">Unrealized PnL</span>
            <span className={`text-sm font-bold ${wallet.unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {wallet.unrealized_pnl >= 0 ? "+" : ""}{wallet.unrealized_pnl.toLocaleString(undefined, { minimumFractionDigits: 2 })} USDT
            </span>
            <button onClick={handleReset} className="mt-1 text-[10px] font-bold text-yellow-500 hover:underline">Reset Wallet</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6 space-y-6">
          <h2 className="text-sm font-bold text-white">Eksekusi Cepat Demo</h2>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-400">Aset Swarm</label>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="w-full rounded-md border border-[#1E293B] bg-[#020617] px-3 py-2.5 text-sm text-white focus:outline-none focus:border-yellow-500"
              >
                {assetsList.map((a) => (
                  <option key={a.symbol} value={a.symbol}>{a.symbol}</option>
                ))}
              </select>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setSide("long")}
                className={`flex-1 rounded py-2 text-xs font-bold transition-all duration-150 ${
                  side === "long" ? "bg-emerald-500 text-slate-950" : "bg-slate-800 text-slate-400"
                }`}
              >LONG</button>
              <button
                onClick={() => setSide("short")}
                className={`flex-1 rounded py-2 text-xs font-bold transition-all duration-150 ${
                  side === "short" ? "bg-red-500 text-slate-950" : "bg-slate-800 text-slate-400"
                }`}
              >SHORT</button>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-400">Ukuran Order (USDT)</label>
              <input
                type="number"
                value={sizeUsdt}
                onChange={(e) => setSizeUsdt(Math.max(1, Number(e.target.value)))}
                className="w-full rounded-md border border-[#1E293B] bg-[#020617] px-3 py-2 text-sm text-white focus:outline-none focus:border-yellow-500"
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold text-slate-400">
                <label>Leverage</label>
                <span>{leverage}x</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={leverage}
                onChange={(e) => setLeverage(Number(e.target.value))}
                className="w-full accent-yellow-500"
              />
            </div>

            <button
              onClick={handleOpen}
              disabled={submitting}
              className="w-full rounded-md bg-yellow-500 py-3 text-sm font-bold text-slate-950 transition-all duration-150 hover:bg-yellow-400 disabled:opacity-50"
            >
              {submitting ? "Memproses..." : `Buka ${side.toUpperCase()} Posisi`}
            </button>
          </div>
        </div>

        <div className="lg:col-span-2 rounded-lg border border-[#1E293B] bg-[#0F172A] p-6">
          <div className="mb-6 flex border-b border-[#1E293B]">
            <button
              onClick={() => setActiveTab("open")}
              className={`pb-3 text-sm font-semibold transition-all duration-150 ${
                activeTab === "open"
                  ? "border-b-2 border-yellow-500 text-yellow-500"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Posisi Aktif ({positions.length})
            </button>
            <button
              onClick={() => setActiveTab("history")}
              className={`ml-6 pb-3 text-sm font-semibold transition-all duration-150 ${
                activeTab === "history"
                  ? "border-b-2 border-yellow-500 text-yellow-500"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Histori Posisi
            </button>
          </div>

          {activeTab === "open" ? (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs text-slate-300">
                <thead className="border-b border-[#1E293B] text-slate-400 uppercase font-bold">
                  <tr>
                    <th className="pb-2">Aset</th>
                    <th className="pb-2">Side</th>
                    <th className="pb-2 text-right">Ukuran</th>
                    <th className="pb-2 text-right">Entry</th>
                    <th className="pb-2 text-right">Mark Price</th>
                    <th className="pb-2 text-right">Leverage</th>
                    <th className="pb-2 text-right">Margin</th>
                    <th className="pb-2 text-right">Unrealized PnL</th>
                    <th className="pb-2 text-center">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1E293B]/50">
                  {positions.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-4 text-center text-slate-500">Tidak ada posisi demo terbuka</td>
                    </tr>
                  ) : (
                    positions.map((pos) => {
                      const entryPriceVal = Number(pos.entry_price);
                      const sizeUsdtVal = Number(pos.size_usdt);
                      const marginVal = Number(pos.margin);
                      const feeVal = pos.fee ? Number(pos.fee) : 0.0;
                      return (
                        <tr key={pos.id} className="hover:bg-[#1E293B]/20">
                          <td className="py-3 font-semibold text-white">{pos.symbol.split("-")[0]}</td>
                          <td className={`py-3 font-bold uppercase ${pos.side === "long" ? "text-emerald-400" : "text-red-400"}`}>{pos.side}</td>
                          <td className="py-3 text-right">${sizeUsdtVal.toLocaleString()}</td>
                          <td className="py-3 text-right">${entryPriceVal.toLocaleString()}</td>
                          <td className="py-3 text-right">${pos.mark_price ? Number(pos.mark_price).toLocaleString() : entryPriceVal.toLocaleString()}</td>
                          <td className="py-3 text-right">{pos.leverage}x</td>
                          <td className="py-3 text-right">${marginVal.toLocaleString()}</td>
                          <td className={`py-3 text-right font-bold ${pos.unrealized_pnl && pos.unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>\n                            {pos.unrealized_pnl && pos.unrealized_pnl >= 0 ? "+" : ""}{pos.unrealized_pnl ? pos.unrealized_pnl.toFixed(2) : "0.00"}\n                          </td>
                          <td className="py-3 text-center">
                            <button onClick={() => handleClose(pos.id)} className="rounded bg-red-500/10 px-2.5 py-1 text-[10px] font-bold text-red-400 border border-red-500/20 hover:bg-red-500/20">Close</button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs text-slate-300">
                <thead className="border-b border-[#1E293B] text-slate-400 uppercase font-bold">
                  <tr>
                    <th className="pb-2">Aset</th>
                    <th className="pb-2">Side</th>
                    <th className="pb-2 text-right">Size</th>
                    <th className="pb-2 text-right">Entry</th>
                    <th className="pb-2 text-right">Exit</th>
                    <th className="pb-2 text-right">PnL</th>
                    <th className="pb-2 text-right">Fee</th>
                    <th className="pb-2">Alasan Tutup</th>
                    <th className="pb-2 text-right">Waktu</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1E293B]/50">
                  {history.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-4 text-center text-slate-500">Belum ada transaksi historis demo</td>
                    </tr>
                  ) : (
                    history.map((pos) => {
                      const sizeUsdtVal = Number(pos.size_usdt);
                      const entryPriceVal = Number(pos.entry_price);
                      const exitPriceVal = pos.exit_price ? Number(pos.exit_price) : 0;
                      const pnlVal = pos.pnl ? Number(pos.pnl) : 0;
                      const feeVal = pos.fee ? Number(pos.fee) : 0;
                      return (
                        <tr key={pos.id} className="hover:bg-[#1E293B]/20">
                          <td className="py-3 font-semibold text-white">{pos.symbol.split("-")[0]}</td>
                          <td className={`py-3 font-bold uppercase ${pos.side === "long" ? "text-emerald-400" : "text-red-400"}`}>{pos.side}</td>
                          <td className="py-3 text-right">${sizeUsdtVal.toLocaleString()}</td>
                          <td className="py-3 text-right">${entryPriceVal.toLocaleString()}</td>
                          <td className="py-3 text-right">${exitPriceVal ? exitPriceVal.toLocaleString() : "-"}</td>
                          <td className={`py-3 text-right font-bold ${pnlVal >= 0 ? "text-emerald-400" : "text-red-400"}`}>\n                            {pnlVal >= 0 ? "+" : ""}{pnlVal.toFixed(2)}\n                          </td>
                          <td className="py-3 text-right">${feeVal.toFixed(4)}</td>
                          <td className="py-3 capitalize">
                            <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${pos.close_reason === "liquidation" ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-slate-800 text-slate-300"}`}>
                              {pos.close_reason}
                            </span>
                          </td>
                          <td className="py-3 text-right text-slate-400">
                            {pos.closed_at ? new Date(pos.closed_at).toLocaleTimeString() : "-"}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
