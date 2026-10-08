import { useState, type FormEvent } from "react";
import { Download, KeyRound, Trash2 } from "lucide-react";

import { ApiError } from "../../api/client";
import * as api from "../../api/endpoints";
import { useAuth } from "../../auth/AuthContext";
import { saveBlob } from "../../lib/download";
import { Button } from "../common/Button";
import { Modal } from "../common/Modal";
import { useToast } from "../common/Toast";

const INPUT =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

const LABEL = "block text-xs font-semibold text-slate-700 dark:text-slate-200";

/** The phrase a user must type to delete their account. */
export const DELETE_PHRASE = "DELETE";

function message(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: typeof Download;
  children: React.ReactNode;
}) {
  return (
    <section
      aria-label={title}
      className="space-y-3 border-t border-slate-200 pt-4 first:border-t-0 first:pt-0 dark:border-slate-800"
    >
      <h3 className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-100">
        <Icon aria-hidden="true" className="h-4 w-4 text-slate-500" />
        {title}
      </h3>
      {children}
    </section>
  );
}

function ExportSection() {
  const { notify } = useToast();
  const [busy, setBusy] = useState(false);

  const onExport = async () => {
    setBusy(true);
    try {
      const { blob, filename } = await api.exportMyData();
      saveBlob(blob, filename || "cogniseek-export.json");
      notify("Your data export is downloading.", "success");
    } catch (error) {
      notify(message(error, "Could not export your data."), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Section title="Export my data" icon={Download}>
      <p className="text-xs text-slate-600 dark:text-slate-400">
        A JSON file with your profile, connected accounts (names only), folders, indexing history and the list
        of indexed files. No file contents, tokens or passwords.
      </p>
      <Button onClick={() => void onExport()} disabled={busy}>
        Export my data
      </Button>
    </Section>
  );
}

function PasswordSection() {
  const { clearSession } = useAuth();
  const { notify } = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.changePassword(current, next);
      notify("Password changed. Please sign in again.", "success");
      clearSession(); // the server ended every session
    } catch (err) {
      setError(message(err, "Could not change the password."));
      setBusy(false);
    }
  };

  return (
    <Section title="Change password" icon={KeyRound}>
      <form onSubmit={(event) => void onSubmit(event)} className="space-y-3">
        <label className={LABEL}>
          Current password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            className={`${INPUT} mt-1`}
          />
        </label>
        <label className={LABEL}>
          New password
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={next}
            onChange={(e) => setNext(e.target.value)}
            aria-describedby="new-password-hint"
            className={`${INPUT} mt-1`}
          />
        </label>
        <p id="new-password-hint" className="text-[11px] text-slate-500 dark:text-slate-400">
          At least 8 characters with a letter and a digit. You will be signed out everywhere.
        </p>
        {error && (
          <p role="alert" className="text-xs font-semibold text-rose-700 dark:text-rose-400">
            {error}
          </p>
        )}
        <Button type="submit" variant="primary" disabled={busy || !current || !next}>
          Change password
        </Button>
      </form>
    </Section>
  );
}

function DeleteSection() {
  const { clearSession } = useAuth();
  const { notify } = useToast();
  const [phrase, setPhrase] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.deleteAccount(password);
      notify("Your account and all of its data were deleted.", "success");
      clearSession();
    } catch (err) {
      setError(message(err, "Could not delete the account."));
      setBusy(false);
    }
  };

  return (
    <Section title="Delete account" icon={Trash2}>
      <p className="text-xs text-slate-600 dark:text-slate-400">
        Permanently deletes your account, your search index, indexing history and connected accounts (access
        is revoked at Google and GitHub). Your original files are not touched. This cannot be undone.
      </p>
      <form onSubmit={(event) => void onSubmit(event)} className="space-y-3">
        <label className={LABEL}>
          Type {DELETE_PHRASE} to confirm
          <input
            value={phrase}
            onChange={(e) => setPhrase(e.target.value)}
            autoComplete="off"
            className={`${INPUT} mt-1`}
          />
        </label>
        <label className={LABEL}>
          Password
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={`${INPUT} mt-1`}
          />
        </label>
        {error && (
          <p role="alert" className="text-xs font-semibold text-rose-700 dark:text-rose-400">
            {error}
          </p>
        )}
        <Button type="submit" variant="danger" disabled={busy || phrase !== DELETE_PHRASE || !password}>
          Delete my account
        </Button>
      </form>
    </Section>
  );
}

/** Account settings: export, change password, delete account. */
export function AccountDialog({ onClose }: { onClose: () => void }) {
  return (
    <Modal title="Account settings" onClose={onClose}>
      <div className="space-y-5">
        <ExportSection />
        <PasswordSection />
        <DeleteSection />
      </div>
    </Modal>
  );
}
