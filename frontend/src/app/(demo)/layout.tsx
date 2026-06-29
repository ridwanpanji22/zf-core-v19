"use client";

import { AuthProvider, useAuth } from "@/app/providers";
import { getWSManager } from "@/lib/ws";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { useEffect } from "react";

function DemoShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  useEffect(() => {
    if (user) {
      getWSManager().connect();
    }
    return () => {
      getWSManager().disconnect();
    };
  }, [user]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#020617]">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-yellow-500 border-t-transparent" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex min-h-screen bg-[#020617]">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="bg-yellow-500/10 border-b border-yellow-500/30 px-4 py-1 text-center text-xs font-bold text-yellow-500">
          MODE DEMO — Paper Trading dengan Saldo Virtual
        </div>
        <Header />
        <main className="flex-1 overflow-y-auto p-8 pt-20 lg:pt-8" id="main-content" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}

export default function DemoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <DemoShell>{children}</DemoShell>
    </AuthProvider>
  );
}
