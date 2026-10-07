import { useId, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderOpen, RefreshCw, Trash2 } from "lucide-react";

import { ApiError } from "../../api/client";
import * as api from "../../api/endpoints";
import { invalidateIndexState, useFolders } from "../../api/queries";
import type { JobWithHistory, PlatformDetail } from "../../api/types";
import { isActiveJob } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { usePlatformActions } from "../../hooks/usePlatformActions";
import { formatDateTime, formatRelative } from "../../lib/format";
import { Button } from "../common/Button";
import { ConfirmDialog } from "../common/ConfirmDialog";
import { Skeleton } from "../common/Spinner";
import { useToast } from "../common/Toast";

interface Props {
  detail: PlatformDetail | undefined;
  job: JobWithHistory | undefined;
}

export function LocalFoldersCard({ detail, job }: Props) {
  const { userId } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const { startIndexing } = usePlatformActions();
  const folders = useFolders();
  const inputId = useId();
  const [path, setPath] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const refresh = () => invalidateIndexState(queryClient, userId);

  const add = useMutation({
    mutationFn: (folder: string) => api.addFolder(folder),
    onSuccess: () => {
      setPath("");
      setFieldError(null);
      notify("Folder added. Index it to make its files searchable.", "success");
    },
    // Validation messages come from the backend (not a folder, outside the allowed roots, …).
    onError: (error) =>
      setFieldError(error instanceof ApiError ? error.message : "Could not add the folder."),
    onSettled: refresh,
  });

  const remove = useMutation({
    mutationFn: (folder: string) => api.removeFolder(folder),
    onSuccess: (data) => notify(`Folder removed; ${data.purged_files ?? 0} indexed files purged.`, "success"),
    onError: (error) =>
      notify(error instanceof ApiError ? error.message : "Could not remove the folder.", "error"),
    onSettled: () => {
      setRemoving(null);
      void refresh();
    },
  });

  const pick = useMutation({
    mutationFn: api.pickFolder,
    onSuccess: (data) => data.folder && setPath(data.folder),
    onError: (error) =>
      setFieldError(error instanceof ApiError ? error.message : "The folder picker failed."),
  });

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!path.trim()) {
      setFieldError("Enter the full path of a folder on the server, e.g. C:\\Users\\me\\Documents.");
      return;
    }
    add.mutate(path.trim());
  };

  const list = folders.data?.folders ?? [];
  const indexing = job ? isActiveJob(job) : false;

  return (
    <section
      aria-labelledby="local-title"
      className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center gap-3">
        <FolderOpen aria-hidden="true" className="h-6 w-6" />
        <h2 id="local-title" className="flex-1 text-base font-semibold">
          Local storage
        </h2>
        <span className="text-sm text-slate-600 dark:text-slate-400">
          {detail?.indexed_files ?? 0} files · last indexed{" "}
          <span title={formatDateTime(detail?.last_indexed_at)}>
            {detail?.last_indexed_at ? formatRelative(detail.last_indexed_at) : "never"}
          </span>
        </span>
      </div>

      <form onSubmit={onSubmit} noValidate className="space-y-2">
        <label htmlFor={inputId} className="text-sm font-medium">
          Add a folder (path on the machine running the backend)
        </label>
        <div className="flex flex-wrap gap-2">
          <input
            id={inputId}
            value={path}
            onChange={(event) => {
              setPath(event.target.value);
              setFieldError(null);
            }}
            aria-invalid={fieldError ? true : undefined}
            aria-describedby={fieldError ? `${inputId}-error` : undefined}
            placeholder="C:\Users\me\Documents"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
          {folders.data?.picker_available && (
            <Button onClick={() => pick.mutate()} disabled={pick.isPending}>
              Browse…
            </Button>
          )}
          <Button type="submit" variant="primary" disabled={add.isPending}>
            Add folder
          </Button>
        </div>
        {fieldError && (
          <p id={`${inputId}-error`} role="alert" className="text-sm text-rose-700 dark:text-rose-300">
            {fieldError}
          </p>
        )}
      </form>

      {folders.isPending ? (
        <Skeleton className="h-10" />
      ) : folders.isError ? (
        <p className="text-sm text-rose-700 dark:text-rose-300">
          Could not load folders: {folders.error.message}
        </p>
      ) : list.length === 0 ? (
        <p className="text-sm text-slate-600 dark:text-slate-400">No folders registered yet.</p>
      ) : (
        <ul
          aria-label="Registered folders"
          className="divide-y divide-slate-200 rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-800"
        >
          {list.map((folder) => (
            <li key={folder} className="flex items-center gap-2 px-3 py-2 text-sm">
              <span className="min-w-0 flex-1 break-all">{folder}</span>
              <button
                type="button"
                onClick={() => setRemoving(folder)}
                aria-label={`Remove folder ${folder}`}
                className="rounded-md p-1.5 text-rose-700 hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-950"
              >
                <Trash2 aria-hidden="true" className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div>
        <Button
          variant="primary"
          disabled={list.length === 0 || indexing || startIndexing.isPending}
          onClick={() => startIndexing.mutate({ priority: "local", platforms: ["local"] })}
        >
          <RefreshCw aria-hidden="true" className="h-4 w-4" />
          {indexing ? "Indexing…" : "Index local folders"}
        </Button>
      </div>

      {removing && (
        <ConfirmDialog
          title="Remove this folder?"
          confirmLabel="Remove and purge"
          danger
          busy={remove.isPending}
          onCancel={() => setRemoving(null)}
          onConfirm={() => remove.mutate(removing)}
        >
          <p className="break-all font-medium">{removing}</p>
          <p>
            Its files are removed from the search index (files covered by another registered folder stay). The
            files on disk are not touched.
          </p>
        </ConfirmDialog>
      )}
    </section>
  );
}
