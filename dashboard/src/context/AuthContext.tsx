import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import api from "../lib/api";

interface User {
  sub: string;
  username: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (username: string, password: string, totpCode?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

function parseJwt(token: string): User | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return { sub: payload.sub, username: payload.username, role: payload.role };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const token = localStorage.getItem("access_token");
    return token ? parseJwt(token) : null;
  });

  const login = useCallback(async (username: string, password: string, totpCode?: string) => {
    const { data } = await api.post("/auth/login", {
      username,
      password,
      totp_code: totpCode || undefined,
    });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setUser(parseJwt(data.access_token));
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, isAuthenticated: !!user, login, logout }),
    [user, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
