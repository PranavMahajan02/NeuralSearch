import { motion } from "motion/react";
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react";

import type { CloudPlatform } from "../../api/endpoints";
import { usePlatformActions } from "../../hooks/usePlatformActions";
import { platformLabel } from "../../lib/platforms";
import { PlatformLogo } from "../common/Badges";
import { FolderManager } from "../platforms/FolderManager";
import { OnboardingFrame } from "./OnboardingFrame";

export interface ConnectionState {
  google_drive: { connected: boolean | undefined; account: string | null | undefined };
  github: { connected: boolean | undefined; account: string | null | undefined };
  localFolders: number;
}

function ConnectedBadge() {
  return (
    <motion.span
      initial={{ scale: 0.7 }}
      animate={{ scale: 1 }}
      className="flex items-center gap-1 rounded-full border border-emerald-100 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300"
    >
      <CheckCircle2 aria-hidden="true" className="h-3 w-3" />
      Connected
    </motion.span>
  );
}

function CloudCard({
  platform,
  state,
  index,
}: {
  platform: CloudPlatform;
  state: ConnectionState["github"];
  index: number;
}) {
  const { connect } = usePlatformActions();
  const label = platformLabel(platform);

  return (
    <motion.section
      aria-labelledby={`onb-${platform}`}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      className={`flex min-h-[11rem] flex-col justify-between rounded-xl border bg-white p-5 transition-all duration-300 dark:bg-slate-900 ${
        state.connected
          ? "border-blue-200 shadow-xs ring-2 ring-blue-500/10 dark:border-blue-800/80"
          : "border-slate-200/80 hover:border-slate-300 hover:shadow-xs dark:border-slate-800/80"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="rounded-lg border border-slate-100 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950">
          <PlatformLogo platform={platform} className="h-6 w-6" />
        </div>
        {state.connected && <ConnectedBadge />}
      </div>
      <div>
        <h2
          id={`onb-${platform}`}
          className="mt-2 font-display text-base font-bold text-slate-800 dark:text-white"
        >
          {label}
        </h2>
        {state.connected && state.account && (
          <p className="truncate text-[11px] text-slate-600 dark:text-slate-400">{state.account}</p>
        )}
        {!state.connected && (
          <button
            type="button"
            disabled={connect.isPending || state.connected === undefined}
            onClick={() => connect.mutate(platform)}
            className="mt-3 w-full cursor-pointer rounded-lg bg-blue-600 px-3 py-2 text-center text-xs font-semibold text-white shadow-xs transition-all duration-200 hover:bg-blue-700 active:scale-97 disabled:bg-slate-200 disabled:text-slate-700"
          >
            Connect {label}
          </button>
        )}
      </div>
    </motion.section>
  );
}

interface Props {
  state: ConnectionState;
  onNext: () => void;
  onSkip: () => void;
  skipping: boolean;
}

/** Step 1: connect Drive / GitHub (OAuth returns here) and add local folders. */
export function ConnectStep({ state, onNext, onSkip, skipping }: Props) {
  const someConnected = !!state.google_drive.connected || !!state.github.connected || state.localFolders > 0;

  return (
    <OnboardingFrame
      step={1}
      stepLabel="Set Up Integrations"
      icon={Sparkles}
      tone="blue"
      title="Connect Your Platforms"
      intro="Choose the platforms CogniSeek should index. You can search across all of them at once, and connect more later from the Platforms page."
      onSkip={onSkip}
      skipping={skipping}
    >
      <div className="mx-auto mt-10 grid w-full max-w-4xl grid-cols-1 gap-4 sm:grid-cols-2">
        <CloudCard platform="google_drive" state={state.google_drive} index={0} />
        <CloudCard platform="github" state={state.github} index={1} />
        <motion.section
          aria-labelledby="onb-local"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className={`rounded-xl border bg-white p-5 sm:col-span-2 dark:bg-slate-900 ${
            state.localFolders > 0
              ? "border-blue-200 ring-2 ring-blue-500/10 dark:border-blue-800/80"
              : "border-slate-200/80 dark:border-slate-800/80"
          }`}
        >
          <div className="mb-4 flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800/60">
            <div className="flex items-center gap-3">
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-2.5 dark:border-slate-800 dark:bg-slate-950">
                <PlatformLogo platform="local" className="h-6 w-6" />
              </div>
              <div>
                <h2
                  id="onb-local"
                  className="font-display text-base font-bold text-slate-800 dark:text-white"
                >
                  Local Storage
                </h2>
                <p className="text-[11px] text-slate-600 dark:text-slate-400">
                  Add the folders to index. Only files inside them are searchable.
                </p>
              </div>
            </div>
            {state.localFolders > 0 && <ConnectedBadge />}
          </div>
          <FolderManager />
        </motion.section>
      </div>

      <div className="mx-auto mt-12 flex w-full max-w-sm flex-col items-center gap-3">
        <button
          type="button"
          disabled={!someConnected}
          onClick={onNext}
          className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3.5 text-sm font-semibold text-white shadow-md shadow-blue-100 transition-all duration-300 hover:bg-blue-700 active:translate-y-[1px] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-700 disabled:shadow-none dark:shadow-none dark:disabled:bg-slate-800 dark:disabled:text-slate-300"
        >
          Continue to Priority Indexing
          <ArrowRight aria-hidden="true" className="h-4 w-4" />
        </button>
        <p className="text-center text-[11px] text-slate-600 dark:text-slate-400">
          {someConnected
            ? "Great! You can connect more later on the Platforms page."
            : "Connect at least one platform to continue."}
        </p>
      </div>
    </OnboardingFrame>
  );
}
