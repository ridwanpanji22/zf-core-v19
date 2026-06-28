"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { isAuthenticated, getAccessToken, clearTokens } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

interface User {
  id: number;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  role: string;
  status: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const fetchUser = async () => {
    const res = await apiFetch<User>("/api/auth/me");
    if (res.success && res.data) {
      setUser(res.data);
    } else {
      clearTokens();
      setUser(null);
      if (pathname !== "/login") {
        router.push("/login");
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    if (isAuthenticated()) {
      fetchUser();
    } else {
      setLoading(false);
      if (pathname !== "/login") {
        router.push("/login");
      }
    }
  }, [pathname]);

  const logout = async () => {
    await apiFetch("/api/auth/logout", { method: "POST" });
    clearTokens();
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
