"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { api, tokenStore } from "./api";
import type { Me, Tokens } from "./types";

interface AuthState {
  me: Me | null;
  loading: boolean;
  signup: (email: string, password: string, fullName?: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refreshMe = useCallback(async () => {
    if (!tokenStore.access) {
      setMe(null);
      return;
    }
    try {
      setMe(await api.me());
    } catch {
      tokenStore.clear();
      setMe(null);
    }
  }, []);

  useEffect(() => {
    refreshMe().finally(() => setLoading(false));
  }, [refreshMe]);

  const afterAuth = useCallback(
    async (tokens: Tokens) => {
      tokenStore.set(tokens);
      await refreshMe();
    },
    [refreshMe]
  );

  const signup = useCallback(
    async (email: string, password: string, fullName?: string) => {
      await afterAuth(await api.signup(email, password, fullName));
    },
    [afterAuth]
  );

  const login = useCallback(
    async (email: string, password: string) => {
      await afterAuth(await api.login(email, password));
    },
    [afterAuth]
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setMe(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{ me, loading, signup, login, logout, refreshMe }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
