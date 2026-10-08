import { useState } from "react";
import { AlertTriangle } from "lucide-react";

import type { CloudPlatform } from "../../api/endpoints";
import type { JobWithHistory, PlatformDetail } from "../../api/types";
import { isActiveJob } from "../../api/types";
import { usePlatformActions } from "../../hooks/usePlatformActions";
import { formatDateTime, formatRelative } from "../../lib/format";
import { platformLabel } from "../../lib/platforms";
import { PlatformLogo } from "../common/Badges";
import { ConfirmDialog } from "../common/ConfirmDialog";

interface CloudPlatformCardProps {
  platform: CloudPlatform;
  connected: boolean | undefined;
  account: string | null | undefined;
  detail: PlatformDetail | undefined;
  job: JobWithHistory | undefined;
  statusError?: string;
}

/** A failed job whose message asks the user to reconnect (expired token, missing scope). */
export function reconnectReason(
  connected: boolean | undefined,
  job: JobWithHistory | undefined,
): string | null {
  if (connected || !job || job.status !== "failed" || !job.error_message) return null;
  return /reconnect|expired|permission/i.test(job.error_message) ? job.error_message : null;
}

export const SMALL_BUTTON =
  "cursor-pointer rounded-lg px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-all active:scale-97";

export function CloudPlatformCard({
  platform,
  connected,
  account,
  detail,
  job,
  statusError,
}: CloudPlatformCardProps) {
  const { connect, disconnect, startIndexing } = usePlatformActions();
  const [confirming, setConfirming] = useState(false);
  const label = platformLabel(platform);
  const reconnect = reconnectReason(connected, job);
  const indexing = job ? isActiveJob(job) : false;
  const status = indexing ? "🟡 Indexing..." : connected ? "🟢 Connected" : "⚪ Not Connected";

  return (
    <section
      aria-labelledby={`${platform}-title`}
      className={`flex flex-col gap-4 rounded-xl border p-4 transition-all ${
        connected
          ? "border-blue-200 bg-slate-50/50 dark:border-blue-900/60 dark:bg-slate-950/40"
          : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="rounded-lg border border-slate-100 bg-white p-2 dark:border-slate-800 dark:bg-slate-900">
            <PlatformLogo platform={platform} className="h-6 w-6" />
          </div>
          <div className="min-w-0">
            <h2
              id={`${platform}-title`}
              className="truncate text-xs font-bold text-slate-800 dark:text-slate-100"
            >
              {label}
            </h2>
            <span className="mt-0.5 block text-[10px] text-slate-500 dark:text-slate-400">
              {connected === undefined ? "Checking…" : status}
            </span>
          </div>
        </div>

        {connected ? (
          <div className="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              disabled={indexing || startIndexing.isPending}
              onClick={() => startIndexing.mutate({ priority: platform, platforms: [platform] })}
              className={`${SMALL_BUTTON} bg-blue-600 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-700`}
            >
              {indexing ? "Indexing…" : "Re-index"}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className={`${SMALL_BUTTON} bg-rose-50 text-rose-700 hover:bg-rose-100 dark:bg-rose-950/30 dark:text-rose-300`}
            >
              Disconnect
            </button>
          </div>
        ) : (
          <button
            type="button"
            disabled={connect.isPending || connected === undefined}
            onClick={() => connect.mutate(platform)}
            className={`${SMALL_BUTTON} bg-slate-900 text-white hover:bg-slate-800 disabled:bg-slate-200 disabled:text-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white`}
          >
            {reconnect ? "Reconnect" : "Connect"}
          </button>
        )}
      </div>

      {statusError && (
        <p className="text-xs text-rose-700 dark:text-rose-300">Status unavailable: {statusError}</p>
      )}

      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
        <dt className="text-slate-500 dark:text-slate-400">Account</dt>
        <dd className="truncate font-semibold text-slate-700 dark:text-slate-300">
          {connected && account ? account : "—"}
        </dd>
        <dt className="text-slate-500 dark:text-slate-400">Indexed files</dt>
        <dd className="font-mono font-semibold text-slate-700 dark:text-slate-300">
          {detail?.indexed_files ?? 0}
        </dd>
        <dt className="text-slate-500 dark:text-slate-400">Last indexed</dt>
        <dd
          className="font-mono font-semibold text-slate-700 dark:text-slate-300"
          title={formatDateTime(detail?.last_indexed_at)}
        >
          {detail?.last_indexed_at ? formatRelative(detail.last_indexed_at) : "Never"}
        </dd>
      </dl>

      {reconnect && (
        <div
          role="alert"
          className="flex gap-2 rounded-lg border border-amber-100 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100"
        >
          <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{reconnect}</p>
        </div>
      )}

      {confirming && (
        <ConfirmDialog
          title={`Disconnect ${label}?`}
          confirmLabel="Disconnect"
          danger
          busy={disconnect.isPending}
          option={`Also remove the ${detail?.indexed_files ?? 0} indexed ${label} files from search`}
          onCancel={() => setConfirming(false)}
          onConfirm={(purge) =>
            disconnect.mutate({ platform, purge }, { onSettled: () => setConfirming(false) })
          }
        >
          <p>
            CogniSeek revokes its access to your {label} account. Files already indexed stay searchable unless
            you remove them.
          </p>
        </ConfirmDialog>
      )}
    </section>
  );
}
