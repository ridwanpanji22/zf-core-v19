"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/app/providers";
import { LayoutDashboard, Settings, ShieldAlert, LogOut } from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

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

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-[#1E293B] bg-[#0F172A] text-slate-200">
      <div className="flex h-16 items-center justify-center border-b border-[#1E293B] px-6">
        <Link href="/" className="text-xl font-bold tracking-wider text-white">
          ZF-CORE <span className="text-[#00FF88]">V19.0</span>
        </Link>
      </div>

      <nav className="flex-1 space-y-1 px-4 py-6">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.path}
              href={item.path}
              className={`flex items-center gap-3 rounded-md px-4 py-3 text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? "bg-[#1E293B] text-[#00FF88] border-l-2 border-[#00FF88]"
                  : "hover:bg-[#1E293B]/50 hover:text-white"
              }`}
            >
              <Icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[#1E293B] p-4">
        <div className="flex items-center gap-3 px-2 py-3">
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.display_name || "User"}
              className="h-9 w-9 rounded-full"
            />
          ) : (
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#1E293B] font-bold text-[#00FF88]">
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
          className="mt-2 flex w-full items-center gap-3 rounded-md px-2 py-3 text-sm font-medium text-red-400 transition-colors duration-150 hover:bg-red-500/10 hover:text-red-300"
        >
          <LogOut className="h-5 w-5" />
          Keluar
        </button>
      </div>
    </aside>
  );
}
