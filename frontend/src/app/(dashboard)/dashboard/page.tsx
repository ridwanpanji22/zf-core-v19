import AssetTable from "@/components/AssetTable";
import PredictionTable from "@/components/PredictionTable";
import SessionComparison from "@/components/SessionComparison";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Dashboard Utama</h1>
        <p className="text-sm text-[#94A3B8]">
          Pemantauan real-time aset Swarm.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <AssetTable />
        </div>
        <div className="space-y-8">
          <PredictionTable />
          <SessionComparison />
        </div>
      </div>
    </div>
  );
}
