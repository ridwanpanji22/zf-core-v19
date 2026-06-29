"use client";

import { AuthProvider, useAuth } from "@/app/providers";
import { getWSManager } from "@/lib/ws";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { useEffect } from "react";

function DashboardShell({ children }: { children: React.ReactNode }) {
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
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#00FF88] border-t-transparent" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex min-h-screen bg-[#020617]">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        {/* pt-16 on mobile to clear the fixed hamburger button; lg:pt-0 restores normal flow */}
        <main className="flex-1 overflow-y-auto p-8 pt-20 lg:pt-8" id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <DashboardShell>{children}</DashboardShell>
    </AuthProvider>
  );
}
