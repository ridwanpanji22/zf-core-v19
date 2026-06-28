"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { ApiKey } from "@/lib/types";

export default function DemoLiveToggle() {
  const router = useRouter();
  const pathname = usePathname();
  const [hasApiKey, setHasApiKey] = useState(false);
  const isDemo = pathname.startsWith("/demo");

  useEffect(() => {
    const checkKeys = async () => {
      const res = await apiFetch<ApiKey[]>("/api/user/api-keys");
      if (res.success && res.data && res.data.length > 0) {
        setHasApiKey(true);
      }
    };
    checkKeys();
  }, [pathname]);

  const handleToggle = () => {
    if (isDemo) {
      if (!hasApiKey) {
        alert("Harap masukkan API Key OKX Anda di menu Settings terlebih dahulu untuk menggunakan Live Mode.");
        return;
      }
      router.push("/dashboard");
    } else {
      router.push("/demo");
    }
  };

  return (
    <div className="flex items-center rounded-md bg-[#1E293B] p-0.5 border border-[#334155]">
      <button
        onClick={() => isDemo && handleToggle()}
        className={`rounded px-3 py-1.5 text-xs font-bold transition-all duration-150 ${
          !isDemo
            ? "bg-[#00FF88] text-[#020617] shadow"
            : "text-slate-400 hover:text-white"
        }`}
      >
        LIVE
      </button>
      <button
        onClick={() => !isDemo && handleToggle()}
        className={`rounded px-3 py-1.5 text-xs font-bold transition-all duration-150 ${
          isDemo
            ? "bg-yellow-500 text-[#020617] shadow"
            : "text-slate-400 hover:text-white"
        }`}
      >
        DEMO
      </button>
    </div>
  );
}
