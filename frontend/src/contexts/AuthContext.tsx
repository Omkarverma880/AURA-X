import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, isApiError } from "@/lib/api";
import type { AuthResponse, FinancialStatus, User } from "@/types";

interface LoginInput {
  email: string;
  password: string;
}

interface RegisterInput {
  email: string;
  password: string;
  full_name: string;
}

interface AuthContextValue {
  user: User | null;
  financial: FinancialStatus | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  loginWithPhone: (phone: string, code: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  setFinancial: (status: FinancialStatus) => void;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [financial, setFinancialState] = useState<FinancialStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const applyAuthResponse = useCallback((data: AuthResponse) => {
    setUserState(data.user);
    setFinancialState(data.financial);
  }, []);

  const loadSession = useCallback(async () => {
    try {
      const { data } = await api.get<AuthResponse>("/auth/me");
      applyAuthResponse(data);
    } catch (error) {
      if (isApiError(error) && error.status === 401) {
        setUserState(null);
        setFinancialState(null);
      }
      // Network or server errors: leave any existing state as-is rather than
      // bouncing a logged-in user to the login screen on a blip.
    } finally {
      setIsLoading(false);
    }
  }, [applyAuthResponse]);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  const login = useCallback(
    async (input: LoginInput) => {
      const { data } = await api.post<AuthResponse>("/auth/login", input);
      applyAuthResponse(data);
    },
    [applyAuthResponse],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      const { data } = await api.post<AuthResponse>("/auth/register", input);
      applyAuthResponse(data);
    },
    [applyAuthResponse],
  );

  const loginWithPhone = useCallback(
    async (phone: string, code: string, fullName?: string) => {
      const { data } = await api.post<AuthResponse>("/auth/phone/login", {
        phone,
        code,
        full_name: fullName || undefined,
      });
      applyAuthResponse(data);
    },
    [applyAuthResponse],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      setUserState(null);
      setFinancialState(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      financial,
      isLoading,
      isAuthenticated: user !== null,
      login,
      register,
      loginWithPhone,
      logout,
      refresh: loadSession,
      setFinancial: setFinancialState,
      setUser: setUserState,
    }),
    [user, financial, isLoading, login, register, loginWithPhone, logout, loadSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
