import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokenStore } from "../api/client";
import type { User } from "../api/types";

interface AuthCtx {
  user: User | null;
  ready: boolean; // finished checking for an existing session
  login: (email: string, password: string) => Promise<void>;
  register: (b: { name: string; email: string; password: string; org?: string; role?: string }) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  // On boot: if a token exists, validate it by fetching /auth/me.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (tokenStore.get()) {
        try {
          const me = await api.me();
          if (!cancelled) setUser(me);
        } catch {
          tokenStore.clear();
        }
      }
      if (!cancelled) setReady(true);
    })();
    return () => { cancelled = true; };
  }, []);

  // Global 401 handler (fired by the API client).
  useEffect(() => {
    const onUnauthorized = () => { tokenStore.clear(); setUser(null); };
    window.addEventListener("kg-unauthorized", onUnauthorized);
    return () => window.removeEventListener("kg-unauthorized", onUnauthorized);
  }, []);

  const login = async (email: string, password: string) => {
    const r = await api.login({ email, password });
    tokenStore.set(r.access_token);
    setUser(r.user);
  };
  const register = async (b: { name: string; email: string; password: string; org?: string; role?: string }) => {
    const r = await api.register(b);
    tokenStore.set(r.access_token);
    setUser(r.user);
  };
  const logout = () => { tokenStore.clear(); setUser(null); };

  return <Ctx.Provider value={{ user, ready, login, register, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used within AuthProvider");
  return c;
}
