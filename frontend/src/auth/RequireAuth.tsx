import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { FullPageSpinner } from "../components/common/Spinner";
import { useAuth } from "./AuthContext";

/** Renders its children only for a logged-in user; otherwise goes to /login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "checking") return <FullPageSpinner label="Checking your session…" />;

  if (status === "anonymous") return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return <>{children}</>;
}
