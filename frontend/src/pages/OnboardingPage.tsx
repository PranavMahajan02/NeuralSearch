import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import * as api from "../api/endpoints";
import { invalidateIndexState, useDriveStatus, useFolders, useGithubStatus } from "../api/queries";
import type { PlatformName } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ChooseStep } from "../components/onboarding/ChooseStep";
import { ConnectStep, type ConnectionState } from "../components/onboarding/ConnectStep";
import { useToast } from "../components/common/Toast";

/**
 * First-run flow for users with onboarding_completed = false.
 * The step lives in the URL (?step=1|2), so the OAuth return (which lands on
 * "/" and is sent here) resumes at step 1.
 */
export function OnboardingPage() {
  const { user, userId, markOnboarded } = useAuth();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const drive = useDriveStatus();
  const github = useGithubStatus();
  const folders = useFolders();

  const finish = () => {
    markOnboarded();
    void invalidateIndexState(queryClient, userId);
    navigate("/search", { replace: true });
  };

  const skip = useMutation({
    mutationFn: api.skipOnboarding,
    onSuccess: finish,
    onError: (error) =>
      notify(error instanceof ApiError ? error.message : "Could not skip onboarding.", "error"),
  });

  const start = useMutation({
    mutationFn: async ({ priority, platforms }: { priority: PlatformName; platforms: PlatformName[] }) => {
      await api.startIndexing(priority, platforms);
      return api.completeOnboarding();
    },
    onSuccess: finish,
    onError: (error) =>
      notify(error instanceof ApiError ? error.message : "Could not start indexing.", "error"),
  });

  if (user?.onboarding_completed) return <Navigate to="/search" replace />;

  const state: ConnectionState = {
    google_drive: { connected: drive.data?.connected, account: drive.data?.account_email },
    github: { connected: github.data?.connected, account: github.data?.account_name },
    localFolders: folders.data?.folders.length ?? 0,
  };

  const connected: PlatformName[] = [
    ...(state.localFolders > 0 ? (["local"] as const) : []),
    ...(state.google_drive.connected ? (["google_drive"] as const) : []),
    ...(state.github.connected ? (["github"] as const) : []),
  ];

  const step = params.get("step") === "2" && connected.length > 0 ? 2 : 1;
  const goTo = (next: 1 | 2) => setParams(next === 1 ? {} : { step: "2" });

  if (step === 2) {
    return (
      <ChooseStep
        connected={connected}
        starting={start.isPending}
        onStart={(priority) => start.mutate({ priority, platforms: connected })}
        onBack={() => goTo(1)}
        onSkip={() => skip.mutate()}
        skipping={skip.isPending}
      />
    );
  }

  return (
    <ConnectStep
      state={state}
      onNext={() => goTo(2)}
      onSkip={() => skip.mutate()}
      skipping={skip.isPending}
    />
  );
}
