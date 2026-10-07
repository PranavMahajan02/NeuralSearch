import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Navigate, useLocation } from "react-router-dom";

import { invalidateIndexState } from "../api/queries";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/common/Toast";
import { readOAuthReturn } from "../hooks/useOAuthReturn";

/**
 * "/" decides where to go:
 * - onboarding not finished: the onboarding (an OAuth return resumes it at step 1, with the toast);
 * - back from an OAuth provider afterwards: Platforms, with the toast;
 * - otherwise: the dashboard.
 */
export function RootRedirect() {
  const { user, userId } = useAuth();
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

  if (!user?.onboarding_completed) return <Navigate to="/onboarding" replace />;

  return <Navigate to={oauth ? "/platforms" : "/search"} replace />;
}
