import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiClient } from "../api/client";

interface AuthContextValue {
  authenticated: boolean;
  role: string | null;
  actorEmail: string | null;
  actorName: string | null;
  loading: boolean;
  logout: () => void;
  refreshSession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [role, setRole] = useState<string | null>(null);
  const [actorEmail, setActorEmail] = useState<string | null>(null);
  const [actorName, setActorName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const clearIdentity = useCallback(() => {
    setAuthenticated(false);
    setRole(null);
    setActorEmail(null);
    setActorName(null);
  }, []);

  const logout = useCallback(() => {
    void apiClient.post("/auth/logout").catch(() => undefined);
    clearIdentity();
  }, [clearIdentity]);

  const refreshSession = useCallback(async () => {
    try {
      const response = await apiClient.get<{ email: string; name: string | null; role: string }>("/auth/me");
      if (response.data.role === "chat") throw new Error("Console access denied");
      setAuthenticated(true);
      setRole(response.data.role);
      setActorEmail(response.data.email.toLowerCase());
      setActorName(response.data.name || null);
      return true;
    } catch {
      clearIdentity();
      return false;
    }
  }, [clearIdentity]);

  useEffect(() => {
    void refreshSession().finally(() => setLoading(false));
  }, [refreshSession]);

  useEffect(() => {
    const recheck = () => {
      if (!document.hidden) void refreshSession();
    };
    window.addEventListener("focus", recheck);
    document.addEventListener("visibilitychange", recheck);
    window.addEventListener("agent-service-auth-change", recheck);
    return () => {
      window.removeEventListener("focus", recheck);
      document.removeEventListener("visibilitychange", recheck);
      window.removeEventListener("agent-service-auth-change", recheck);
    };
  }, [refreshSession]);

  const value = useMemo(
    () => ({ authenticated, role, actorEmail, actorName, loading, logout, refreshSession }),
    [authenticated, role, actorEmail, actorName, loading, logout, refreshSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}
