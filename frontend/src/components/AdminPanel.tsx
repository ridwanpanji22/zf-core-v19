"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { User } from "@/lib/types";

export default function AdminPanel() {
  const [users, setUsers] = useState<User[]>([]);
  const [configs, setConfigs] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<"users" | "config">("users");
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  const loadAdminData = async () => {
    const [uRes, cRes] = await Promise.all([
      apiFetch<User[]>("/api/admin/users"),
      apiFetch<Record<string, any>>("/api/admin/config"),
    ]);
    if (uRes.success && uRes.data) setUsers(uRes.data);
    if (cRes.success && cRes.data) setConfigs(cRes.data);
    setLoading(false);
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleStatusChange = async (id: number, currentStatus: string) => {
    const nextStatus = currentStatus === "active" ? "suspended" : "active";
    if (confirm(`Ubah status user menjadi ${nextStatus}?`)) {
      const res = await apiFetch(`/api/admin/users/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      if (res.success) {
        await loadAdminData();
      }
    }
  };

  const handleRoleChange = async (id: number, currentRole: string) => {
    const nextRole = currentRole === "super_admin" ? "architect" : "super_admin";
    if (confirm(`Ubah role user menjadi ${nextRole}?`)) {
      const res = await apiFetch(`/api/admin/users/${id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: nextRole }),
      });
      if (res.success) {
        await loadAdminData();
      }
    }
  };

  const handleDeleteUser = async (id: number) => {
    if (confirm("Apakah Anda yakin ingin menghapus user ini secara permanen? Semua data API key dan wallet demo akan ikut terhapus.")) {
      const res = await apiFetch(`/api/admin/users/${id}`, { method: "DELETE" });
      if (res.success) {
        await loadAdminData();
      }
    }
  };

  const handleConfigUpdate = async (key: string, value: any) => {
    setUpdating(true);
    const res = await apiFetch("/api/admin/config", {
      method: "PUT",
      body: JSON.stringify({ key, value }),
    });
    if (res.success) {
      alert(`Konfigurasi ${key} berhasil diperbarui!`);
      await loadAdminData();
    } else {
      alert(res.error?.message || "Gagal memperbarui konfigurasi");
    }
    setUpdating(false);
  };

  const handleSystemAction = async (action: string) => {
    let path = "";
    if (action === "reset_cb") path = "/api/system/circuit-breaker/reset";
    else if (action === "recalibrate") path = "/api/calibration/trigger";

    const res = await apiFetch(path, { method: "POST" });
    if (res.success) {
      alert("Aksi sistem berhasil dipicu!");
    } else {
      alert(res.error?.message || "Gagal memicu aksi sistem");
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
    <div className="space-y-8">
      {/* System Actions Header card */}
      <div className="rounded-lg border border-red-500/20 bg-[#0F172A] p-6 space-y-4">
        <h2 className="text-sm font-bold text-red-500">Proteksi & Kontrol Sistem Darurat</h2>
        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => handleSystemAction("reset_cb")}
            className="rounded-md bg-red-600 px-4 py-2 text-xs font-bold text-white transition-colors duration-150 hover:bg-red-500"
          >
            Reset Circuit Breaker
          </button>
          <button
            onClick={() => handleSystemAction("recalibrate")}
            className="rounded-md bg-purple-600 px-4 py-2 text-xs font-bold text-white transition-colors duration-150 hover:bg-purple-500"
          >
            Picu Kalibrasi Ulang ω
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-[#1E293B] bg-[#0F172A] p-6">
        <div className="mb-6 flex border-b border-[#1E293B]">
          <button
            onClick={() => setActiveTab("users")}
            className={`pb-3 text-sm font-semibold transition-all duration-150 ${
              activeTab === "users"
                ? "border-b-2 border-[#00FF88] text-[#00FF88]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Kelola Pengguna
          </button>
          <button
            onClick={() => setActiveTab("config")}
            className={`ml-6 pb-3 text-sm font-semibold transition-all duration-150 ${
              activeTab === "config"
                ? "border-b-2 border-[#00FF88] text-[#00FF88]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Konfigurasi Global (`system_config`)
          </button>
        </div>

        {activeTab === "users" ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs text-slate-300">
              <thead className="border-b border-[#1E293B] text-slate-400 uppercase font-bold">
                <tr>
                  <th className="pb-2">ID</th>
                  <th className="pb-2">Email</th>
                  <th className="pb-2">Nama</th>
                  <th className="pb-2">Role</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2 text-center">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E293B]/50">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-[#1E293B]/20">
                    <td className="py-3 font-semibold text-white">{user.id}</td>
                    <td className="py-3">{user.email}</td>
                    <td className="py-3 font-medium">{user.display_name || "-"}</td>
                    <td className="py-3 capitalize">
                      <span className={`rounded-full px-2 py-0.5 font-semibold ${
                        user.role === "super_admin" ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-slate-800 text-slate-300"
                      }`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="py-3 capitalize">
                      <span className={`rounded px-1.5 py-0.5 font-bold ${
                        user.status === "active" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}>
                        {user.status}
                      </span>
                    </td>
                    <td className="py-3 flex items-center justify-center gap-2">
                      <button
                        onClick={() => handleStatusChange(user.id, user.status)}
                        className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700 font-bold"
                      >
                        {user.status === "active" ? "Suspend" : "Activate"}
                      </button>
                      <button
                        onClick={() => handleRoleChange(user.id, user.role)}
                        className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700 font-bold"
                      >
                        Promote/Demote
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        className="rounded bg-red-500/10 px-2.5 py-1 text-red-400 border border-red-500/20 hover:bg-red-500/20 font-bold"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="max-w-xl space-y-6">
            <div className="rounded-lg border border-[#1E293B] bg-[#020617] p-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-white">Mode Demo Global</p>
                <p className="text-xs text-slate-400">Aktifkan/nonaktifkan fitur paper trading untuk semua user.</p>
              </div>
              <select
                disabled={updating}
                value={configs["demo_mode_enabled"] ?? "true"}
                onChange={(e) => handleConfigUpdate("demo_mode_enabled", e.target.value)}
                className="rounded border border-[#1E293B] bg-[#0F172A] px-3 py-1.5 text-xs text-white"
              >
                <option value="true">Aktif</option>
                <option value="false">Nonaktif</option>
              </select>
            </div>

            <div className="rounded-lg border border-[#1E293B] bg-[#020617] p-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-white">Saldo Demo Awal</p>
                <p className="text-xs text-slate-400">Jumlah saldo virtual default (USDT) saat user auto-register.</p>
              </div>
              <input
                type="number"
                disabled={updating}
                value={configs["demo_initial_balance"] ?? 10000}
                onBlur={(e) => handleConfigUpdate("demo_initial_balance", Number(e.target.value))}
                className="w-24 rounded border border-[#1E293B] bg-[#0F172A] px-3 py-1.5 text-center text-xs text-white focus:outline-none"
              />
            </div>

            <div className="rounded-lg border border-[#1E293B] bg-[#020617] p-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-white">Leverage Maksimal Demo</p>
                <p className="text-xs text-slate-400">Batas maksimal leverage yang dapat diatur oleh trader di mode demo.</p>
              </div>
              <input
                type="number"
                disabled={updating}
                value={configs["demo_max_leverage"] ?? 10}
                onBlur={(e) => handleConfigUpdate("demo_max_leverage", Number(e.target.value))}
                className="w-24 rounded border border-[#1E293B] bg-[#0F172A] px-3 py-1.5 text-center text-xs text-white focus:outline-none"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
