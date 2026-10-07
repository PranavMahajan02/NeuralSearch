import { useId, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import * as api from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/common/Button";
import { Spinner } from "../components/common/Spinner";

type Mode = "login" | "register";

function Field({
  label,
  error,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) {
  const id = useId();

  return (
    <div className="space-y-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        required
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
        {...props}
      />
      {error && <p className="text-xs text-slate-600 dark:text-slate-400">{error}</p>}
    </div>
  );
}

export function LoginPage() {
  const { status, login, sessionExpired: expired } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === "authenticated") return <Navigate to="/" replace />;

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      if (mode === "register") await api.register({ name, email, password });
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <main className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-2 text-center">
          <img src="/favicon.svg" alt="" className="h-10 w-10" />
          <h1 className="text-2xl font-bold tracking-tight">CogniSeek</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            One search across your local files, Google Drive and GitHub.
          </p>
        </div>

        <form
          onSubmit={(event) => void onSubmit(event)}
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
          <h2 className="text-lg font-semibold">{mode === "login" ? "Log in" : "Create an account"}</h2>

          {expired && !error && (
            <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-950">
              Your session has expired. Please log in again.
            </p>
          )}
          {error && (
            <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-900">
              {error}
            </p>
          )}

          {mode === "register" && (
            <Field label="Name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
          )}
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            label="Password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={
              mode === "register" ? "8–128 characters, with at least one letter and one digit." : undefined
            }
          />

          <Button type="submit" variant="primary" className="w-full" disabled={busy}>
            {busy ? <Spinner label="Please wait…" /> : mode === "login" ? "Log in" : "Create account"}
          </Button>

          <p className="text-center text-sm text-slate-600 dark:text-slate-300">
            {mode === "login" ? "New to CogniSeek?" : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
              className="font-semibold text-blue-800 hover:underline dark:text-blue-300"
            >
              {mode === "login" ? "Create an account" : "Log in"}
            </button>
          </p>
        </form>
      </main>
    </div>
  );
}
