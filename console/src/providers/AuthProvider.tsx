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
import { loginWithPassword as apiLoginWithPassword } from "../api/auth";
import { listDocuments } from "../api/documents";
import {
  getStoredRole,
  setStoredRole,
  clearStoredRole,
} from "../utils/token-storage";

interface AuthContextValue {
  token: string | null;
  role: string | null;
  loading: boolean;
  loginWithPassword: (password: string) => Promise<void>;
  loginWithToken: (token: string) => Promise<void>;
  logout: () => void;
  ensureValidToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [role, setRole] = useState<string | null>(getStoredRole());
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    clearAuthToken();
    setToken(null);
    clearStoredRole();
    setRole(null);
  }, []);

  const ensureValidToken = useCallback(async () => {
    const current = getAuthToken();
    if (!current) {
      setToken(null);
      setRole(null);
      return false;
    }
    try {
      await listDocuments({ limit: 1, offset: 0 });
      setToken(current);
       setRole(getStoredRole());
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

  const loginWithToken = useCallback(
    async (providedToken: string) => {
      setAuthToken(providedToken.trim());
      setStoredRole(null);
      try {
        await listDocuments({ limit: 1, offset: 0 });
        setToken(providedToken.trim());
        setRole(null);
      } catch (error) {
        logout();
        throw error;
      }
    },
    [logout],
  );

  const loginWithPassword = useCallback(
    async (password: string) => {
      try {
        const response = await apiLoginWithPassword(password.trim());
        setAuthToken(response.token);
        setStoredRole(response.role);
        setToken(response.token);
        setRole(response.role);
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
      role,
      loading,
      loginWithPassword,
      loginWithToken,
      logout,
      ensureValidToken,
    }),
    [token, role, loading, loginWithPassword, loginWithToken, logout, ensureValidToken],
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
