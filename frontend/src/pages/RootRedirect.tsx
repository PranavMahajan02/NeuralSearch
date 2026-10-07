import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate, useLocation } from "react-router-dom";

import * as api from "../api/endpoints";
import { invalidateIndexState } from "../api/queries";
import { useAuth } from "../auth/AuthContext";
import { FullPageSpinner } from "../components/common/Spinner";
import { useToast } from "../components/common/Toast";
import { readOAuthReturn } from "../hooks/useOAuthReturn";

/**
 * "/" decides where to go:
 * - back from an OAuth provider (?github=… / ?google_drive=…): show the result, go to Platforms;
 * - nothing indexed yet: the welcome page; otherwise: search.
 */
export function RootRedirect() {
  const { userId } = useAuth();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  // Read once: the query string is replaced by the redirect below.
  const [oauth] = useState(() => readOAuthReturn(location.search));
  const announced = useRef(false);

  useEffect(() => {
    if (!oauth || announced.current) return;
    announced.current = true;
    notify(oauth.message, oauth.ok ? "success" : "error");
    void invalidateIndexState(queryClient, userId);
  }, [oauth, notify, queryClient, userId]);

  const state = useQuery({
    queryKey: ["user", userId, "login-state"],
    queryFn: api.getLoginState,
    enabled: !oauth,
  });

  if (oauth) return <Navigate to="/platforms" replace />;

  if (state.isPending) return <FullPageSpinner label="Loading…" />;

  return <Navigate to={state.data?.has_indexed ? "/search" : "/welcome"} replace />;
}
