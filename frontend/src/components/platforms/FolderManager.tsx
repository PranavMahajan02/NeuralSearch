import { useId, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { Folder, FolderPlus, Plus, X } from "lucide-react";

import { ApiError } from "../../api/client";
import * as api from "../../api/endpoints";
import { invalidateIndexState, useFolders } from "../../api/queries";
import { useAuth } from "../../auth/AuthContext";
import { ConfirmDialog } from "../common/ConfirmDialog";
import { Skeleton } from "../common/Spinner";
import { useToast } from "../common/Toast";

/**
 * Local folders: type a path (validated by the backend), Browse (only when the
 * backend runs in development), list with Remove (purges their index entries).
 */
export function FolderManager() {
  const { userId } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
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

  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-12">
      <form onSubmit={onSubmit} noValidate className="space-y-3 md:col-span-5">
        <label
          htmlFor={inputId}
          className="block font-mono text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400"
        >
          Add a folder (path on the machine running the backend)
        </label>
        <div className="flex gap-2">
          <input
            id={inputId}
            value={path}
            onChange={(event) => {
              setPath(event.target.value);
              setFieldError(null);
            }}
            aria-invalid={fieldError ? true : undefined}
            aria-describedby={fieldError ? `${inputId}-error` : undefined}
            placeholder="e.g. D:\Research Papers"
            className="min-w-0 flex-grow rounded-xl border border-slate-200 bg-slate-50 p-2.5 font-mono text-xs text-slate-700 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200"
          />
          <button
            type="submit"
            disabled={add.isPending}
            className="flex items-center justify-center gap-1 rounded-xl border border-slate-200 bg-slate-100 px-3 text-xs font-semibold text-slate-700 transition-all hover:bg-slate-200 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <Plus aria-hidden="true" className="h-4 w-4" />
            Add folder
          </button>
        </div>
        {fieldError && (
          <p id={`${inputId}-error`} role="alert" className="text-xs text-rose-700 dark:text-rose-300">
            {fieldError}
          </p>
        )}
        {folders.data?.picker_available && (
          <button
            type="button"
            onClick={() => pick.mutate()}
            disabled={pick.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition-all hover:bg-blue-700 active:scale-98"
          >
            <Folder aria-hidden="true" className="h-4 w-4" />
            Browse… (development only)
          </button>
        )}
      </form>

      <div className="flex min-h-[10rem] flex-col rounded-xl border border-slate-200/60 bg-slate-50/50 p-4 md:col-span-7 dark:border-slate-800 dark:bg-slate-950/40">
        <span className="mb-3 font-mono text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Selected directories ({list.length})
        </span>
        {folders.isPending ? (
          <Skeleton className="h-10" />
        ) : folders.isError ? (
          <p className="text-xs text-rose-700 dark:text-rose-300">
            Could not load folders: {folders.error.message}
          </p>
        ) : list.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-white p-6 text-center dark:border-slate-800 dark:bg-slate-900">
            <FolderPlus aria-hidden="true" className="mb-2 h-8 w-8 text-slate-400 dark:text-slate-600" />
            <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">
              No folders registered yet
            </p>
          </div>
        ) : (
          <ul aria-label="Registered folders" className="max-h-48 space-y-2 overflow-y-auto pr-1">
            <AnimatePresence initial={false}>
              {list.map((folder) => (
                <motion.li
                  key={folder}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="flex items-center justify-between rounded-lg border border-slate-100 bg-white p-2.5 shadow-2xs dark:border-slate-800 dark:bg-slate-900"
                >
                  <span className="flex min-w-0 items-center gap-2.5">
                    <span className="rounded-md bg-blue-50 p-1.5 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                      <Folder aria-hidden="true" className="h-3.5 w-3.5" />
                    </span>
                    <span className="break-all pr-2 font-mono text-xs font-medium text-slate-700 dark:text-slate-300">
                      {folder}
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setRemoving(folder)}
                    aria-label={`Remove folder ${folder}`}
                    className="rounded-md p-1 text-slate-500 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30"
                  >
                    <X aria-hidden="true" className="h-3.5 w-3.5" />
                  </button>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
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
    </div>
  );
}
