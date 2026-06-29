import DemoPanel from "@/components/DemoPanel";

export default function DemoPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Mode Demo</h1>
        <p className="text-sm text-slate-400">
          Paper trading dengan saldo virtual tanpa risiko.
        </p>
      </div>

      <DemoPanel />
    </div>
  );
}
