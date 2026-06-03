"use client";

import * as React from "react";

const TOKEN_KEY = "sfqa.dev.token";

interface AuthState {
  token: string | null;
  setToken: (token: string | null) => void;
  isReady: boolean;
}

const AuthContext = React.createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = React.useState<string | null>(null);
  const [isReady, setIsReady] = React.useState(false);

  // Hydrate from localStorage after mount to avoid SSR/CSR mismatch.
  React.useEffect(() => {
    setTokenState(window.localStorage.getItem(TOKEN_KEY));
    setIsReady(true);
  }, []);

  const setToken = React.useCallback((next: string | null) => {
    setTokenState(next);
    if (next) {
      window.localStorage.setItem(TOKEN_KEY, next);
    } else {
      window.localStorage.removeItem(TOKEN_KEY);
    }
  }, []);

  const value = React.useMemo(
    () => ({ token, setToken, isReady }),
    [token, setToken, isReady],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = React.useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within <AuthProvider>");
  }
  return ctx;
}
