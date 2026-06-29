"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/app/providers";
import { LayoutDashboard, Settings, ShieldAlert, LogOut, Menu, X } from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isDemo = pathname.startsWith("/demo");

  const navItems = [
    {
      name: "Dashboard",
      path: isDemo ? "/demo" : "/dashboard",
      icon: LayoutDashboard,
    },
    {
      name: "Settings",
      path: "/dashboard/settings",
      icon: Settings,
    },
  ];

  if (user?.role === "super_admin") {
    navItems.push({
      name: "Admin Panel",
      path: "/admin",
      icon: ShieldAlert,
    });
  }

  const NavContent = () => (
    <>
      <nav className="flex-1 space-y-1 px-4 py-6" aria-label="Navigasi utama">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.path}
              href={item.path}
              onClick={() => setMobileOpen(false)}
              aria-current={isActive ? "page" : undefined}
              className={`flex items-center gap-3 rounded-md px-4 py-3 text-sm font-medium transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-[#00FF88] focus:ring-offset-1 focus:ring-offset-[#0F172A] ${
                isActive
                  ? "bg-[#1E293B] text-[#00FF88] border-l-2 border-[#00FF88]"
                  : "hover:bg-[#1E293B]/50 hover:text-white"
              }`}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[#1E293B] p-4">
        <div className="flex items-center gap-3 px-2 py-3" aria-label={`Login sebagai ${user?.display_name || user?.email}`}>
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={`Foto profil ${user.display_name || "User"}`}
              className="h-9 w-9 rounded-full"
            />
          ) : (
            <div
              aria-hidden="true"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-[#1E293B] font-bold text-[#00FF88]"
            >
              {user?.email?.charAt(0).toUpperCase()}
            </div>
          )}
          <div className="flex-1 overflow-hidden">
            <p className="truncate text-sm font-semibold text-white">
              {user?.display_name || "User"}
            </p>
            <p className="truncate text-xs text-slate-400">{user?.role}</p>
          </div>
        </div>
        <button
          onClick={logout}
          aria-label="Keluar dari akun"
          className="mt-2 flex w-full items-center gap-3 rounded-md px-2 py-3 text-sm font-medium text-red-400 transition-colors duration-150 hover:bg-red-500/10 hover:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-1 focus:ring-offset-[#0F172A]"
        >
          <LogOut className="h-5 w-5" aria-hidden="true" />
          Keluar
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        className="fixed left-4 top-4 z-50 flex items-center justify-center rounded-md border border-[#1E293B] bg-[#0F172A] p-2 text-slate-200 lg:hidden focus:outline-none focus:ring-2 focus:ring-[#00FF88]"
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label={mobileOpen ? "Tutup menu navigasi" : "Buka menu navigasi"}
        aria-expanded={mobileOpen}
        aria-controls="sidebar-nav"
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar — hidden on mobile unless open, always visible on lg+ */}
      <aside
        id="sidebar-nav"
        className={`fixed inset-y-0 left-0 z-40 flex h-screen w-64 flex-col border-r border-[#1E293B] bg-[#0F172A] text-slate-200 transition-transform duration-200 lg:static lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Sidebar navigasi"
      >
        <div className="flex h-16 items-center justify-center border-b border-[#1E293B] px-6">
          <Link
            href="/"
            className="text-xl font-bold tracking-wider text-white focus:outline-none focus:ring-2 focus:ring-[#00FF88] focus:ring-offset-1 focus:ring-offset-[#0F172A] rounded"
          >
            ZF-CORE <span className="text-[#00FF88]">V19.0</span>
          </Link>
        </div>

        <NavContent />
      </aside>
    </>
  );
}
