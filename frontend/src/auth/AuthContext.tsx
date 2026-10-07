import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { clearToken, getToken, onUnauthorized, setToken } from "../api/client";
import * as api from "../api/endpoints";
import type { User } from "../api/types";

type AuthStatus = "anonymous" | "checking" | "authenticated";

interface AuthValue {
  status: AuthStatus;
  user: User | null;
  /** "" when nobody is logged in. Query keys are scoped by it. */
  userId: string;
  /** True after a 401 ended the session (until the next login). */
  sessionExpired: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [sessionExpired, setSessionExpired] = useState(false);

  const profile = useQuery({
    queryKey: ["profile", token],
    queryFn: ({ signal }) => api.getProfile(signal),
    enabled: token !== null,
    staleTime: Infinity,
    retry: false,
  });

  // Any authenticated call that gets 401 (expired or revoked token) ends the session.
  useEffect(() => {
    onUnauthorized(() => {
      setTokenState(null);
      setSessionExpired(true);
      queryClient.clear();
      navigate("/login", { replace: true });
    });
    return () => onUnauthorized(() => undefined);
  }, [navigate, queryClient]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      queryClient.clear();
      setSessionExpired(false);
      setTokenState(access_token);
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout(); // revokes every token of this user on the server
    } catch {
      /* logging out locally is enough if the server is unreachable */
    }
    clearToken();
    queryClient.clear();
    setTokenState(null);
    navigate("/login", { replace: true });
  }, [navigate, queryClient]);

  const value = useMemo<AuthValue>(() => {
    const user = token && profile.data ? profile.data : null;
    const status: AuthStatus =
      token === null || profile.isError ? "anonymous" : user ? "authenticated" : "checking";

    return { status, user, userId: user?.id ?? "", sessionExpired, login, logout };
  }, [token, profile.data, profile.isError, sessionExpired, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>.");
  return value;
}
