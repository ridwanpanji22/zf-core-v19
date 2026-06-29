"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setTokens, isAuthenticated } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // 1. Check if user already logged in
    if (isAuthenticated()) {
      router.push("/dashboard");
      return;
    }

    // 2. Handle callback redirection credentials
    const access = searchParams.get("access_token");
    const refresh = searchParams.get("refresh_token");
    const err = searchParams.get("error");

    if (err) {
      setError(decodeURIComponent(err));
    } else if (access && refresh) {
      setTokens(access, refresh);
      router.push("/dashboard");
    }
  }, [searchParams, router]);

  const handleGoogleLogin = () => {
    setLoading(true);
    // Redirect to backend OAuth initiator
    window.location.href = "/api/auth/google";
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#020617] px-4">
      <div className="w-full max-w-md space-y-8 rounded-lg border border-[#1E293B] bg-[#0F172A] p-8 shadow-2xl">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold tracking-tight text-white">
            ZF-CORE <span className="text-[#00FF88]">V19.0</span>
          </h2>
          <p className="mt-2 text-sm text-[#94A3B8]">
            Protokol trading kuantitatif AI.
          </p>
        </div>

        {error && (
          <div className="rounded border border-red-500/30 bg-red-500/10 p-3 text-center text-sm text-red-500">
            {error}
          </div>
        )}

        <div className="mt-8 space-y-6">
          <button
            onClick={handleGoogleLogin}
            disabled={loading}
            className="flex w-full items-center justify-center gap-3 rounded-md bg-[#1E293B] px-4 py-3 text-sm font-semibold text-white transition-colors duration-200 hover:bg-[#334155] focus:outline-none focus:ring-2 focus:ring-[#00FF88] focus:ring-offset-2 disabled:opacity-50"
          >
            {loading ? (
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.77c-.98.66-2.23 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
              </svg>
            )}
            Sign in dengan Google
          </button>
        </div>
      </div>
    </div>
  );
}
