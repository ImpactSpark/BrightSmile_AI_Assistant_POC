import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { getMe, logout as apiLogout } from "../api/client";

interface AuthState {
  role: "doctor" | "patient" | "admin" | null;
  id: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
  clear: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<"doctor" | "patient" | "admin" | null>(null);
  const [id, setId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await getMe();
      setRole(me.role);
      setId(me.id);
    } catch {
      setRole(null);
      setId(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(async () => {
    await apiLogout();
    setRole(null);
    setId(null);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <AuthContext.Provider value={{ role, id, loading, refresh, clear }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
