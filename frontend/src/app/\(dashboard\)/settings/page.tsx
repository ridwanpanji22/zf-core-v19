"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { ApiKey } from "@/lib/types";

export default function SettingsPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [label, setLabel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [warning, setWarning] = useState<string | null>(null);

  const loadKeys = async () => {
    const res = await apiFetch<ApiKey[]>("/api/user/api-keys");
    if (res.success && res.data) {
      setKeys(res.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadKeys();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setWarning(null);

    const res = await apiFetch<any>("/api/user/api-keys", {
      method: "POST",
      body: JSON.stringify({ label, api_key: apiKey, secret_key: secretKey, passphrase }),
    });

    if (res.success && res.data) {
      alert("API Key OKX berhasil divalidasi dan disimpan!");
      if (res.data.warning) {
        setWarning(res.data.warning);
      }
      setLabel("");
      setApiKey("");
      setSecretKey("");
      setPassphrase("");
      await loadKeys();
    } else {
      alert(res.error?.message || "Gagal menyimpan API Key. Validasi OKX gagal.");
    }
    setSubmitting(false);
  };

  const handleDelete = async (id: number) => {
    if (confirm("Apakah Anda yakin ingin menghapus API Key ini?")) {
      const res = await apiFetch(`/api/user/api-keys/${id}`, { method: "DELETE" });
      if (res.success) {
        await loadKeys();
      } else {
        alert(res.error?.message || "Gagal menghapus API Key.");
      }
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-white">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#00FF88] border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Pengaturan API Key</h1>
        <p className="text-sm text-slate-400">
          Kelola API Key OKX pribadi untuk integrasi Live Trading.
        </p>
      </div>

      {warning && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-yellow-500">
          {warning}
        </div>
      )}

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
        {/* Add Form */}
        <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6 space-y-4">
          <h2 className="text-base font-bold text-white">Tambah API Key OKX</h2>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-400">Label Deskriptif</label>
              <input
                type="text"
                placeholder="e.g. OKX Live Read Only"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                className="w-full rounded-md border border-[#1E293B] bg-[#020617] px-3 py-2 text-sm text-white focus:outline-none focus:border-[#00FF88]"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-400">API Key</label>
              <input
                type="text"
                placeholder="Masukkan API Key OKX"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                required
                className="w-full rounded-md border border-[#1E293B] bg-[#020617] px-3 py-2 text-sm text-white focus:outline-none focus:border-[#00FF88]"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-400">Secret Key</label>
              <input
                type="password"
                placeholder="Masukkan Secret Key OKX"
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                required
                className="w-full rounded-md border border-[#1E293B] bg-[#020617] px-3 py-2 text-sm text-white focus:outline-none focus:border-[#00FF88]"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-400">Passphrase</label>
              <input
                type="password"
                placeholder="Masukkan Passphrase OKX"
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                required
                className="w-full rounded-md border border-[#1E293B] bg-[#020617] px-3 py-2 text-sm text-white focus:outline-none focus:border-[#00FF88]"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-[#00FF88] py-2.5 text-sm font-bold text-slate-950 transition-all duration-150 hover:bg-[#00CC6D] disabled:opacity-50"
            >
              {submitting ? "Memproses..." : "Simpan API Key"}
            </button>
          </form>
        </div>

        {/* Registered keys list */}
        <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6 space-y-4">
          <h2 className="text-base font-bold text-white">API Key Terdaftar ({keys.length}/3)</h2>
          {keys.length === 0 ? (
            <p className="text-sm text-slate-500">Belum ada API Key terdaftar. Sistem berjalan di mode read-only.</p>
          ) : (
            <div className="space-y-3">
              {keys.map((key) => (
                <div key={key.id} className="rounded-lg border border-[#1E293B] bg-[#020617] p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-white">{key.label || "API Key OKX"}</p>
                    <p className="text-xs text-slate-500">Key: ****{key.api_key_last4}</p>
                    <span className={`mt-1 inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                      key.is_valid ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                    }`}>
                      {key.is_valid ? `${key.permission_level} permissions` : "Kredensial Tidak Valid"}
                    </span>
                  </div>
                  <button
                    onClick={() => handleDelete(key.id)}
                    className="rounded bg-red-500/10 px-3 py-1.5 text-xs font-bold text-red-400 border border-red-500/20 hover:bg-red-500/20"
                  >
                    Hapus
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
