import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getAuthToken, setAuthToken, clearAuthToken } from "../api/client";
import { listDocuments } from "../api/documents";

interface AuthContextValue {
  token: string | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  ensureValidToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    clearAuthToken();
    setToken(null);
  }, []);

  const ensureValidToken = useCallback(async () => {
    const current = getAuthToken();
    if (!current) {
      setToken(null);
      return false;
    }
    try {
      await listDocuments({ limit: 1, offset: 0 });
      setToken(current);
      return true;
    } catch {
      logout();
      return false;
    }
  }, [logout]);

  useEffect(() => {
    (async () => {
      await ensureValidToken();
      setLoading(false);
    })();
  }, [ensureValidToken]);

  const login = useCallback(
    async (providedToken: string) => {
      setAuthToken(providedToken.trim());
      try {
        await listDocuments({ limit: 1, offset: 0 });
        setToken(providedToken.trim());
      } catch (error) {
        logout();
        throw error;
      }
    },
    [logout],
  );

  const value = useMemo(
    () => ({
      token,
      loading,
      login,
      logout,
      ensureValidToken,
    }),
    [token, loading, login, logout, ensureValidToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used within AuthProvider");
  }
  return ctx;
}
