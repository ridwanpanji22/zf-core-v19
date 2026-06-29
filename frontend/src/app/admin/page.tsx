import AdminPanel from "@/components/AdminPanel";

export default function AdminPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Super Admin Control Panel</h1>
        <p className="text-sm text-slate-400">
          Kelola status pengguna, konfigurasi parameter trading, dan proteksi darurat.
        </p>
      </div>

      <AdminPanel />
    </div>
  );
}
