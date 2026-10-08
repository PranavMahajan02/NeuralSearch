import { useId, useState, type FormEvent, type InputHTMLAttributes } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, CheckCircle2, Lock, Mail, User, type LucideIcon } from "lucide-react";

import { ApiError } from "../api/client";
import * as api from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { FloatingBadges } from "../components/auth/FloatingBadges";
import { LoginLogo, ThemeToggle } from "../components/common/Brand";

type View = "options" | "sign_in" | "sign_up";

const INPUT =
  "w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm text-slate-800 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100 dark:placeholder-slate-500";

function Field({
  label,
  icon: Icon,
  hint,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; icon: LucideIcon; hint?: string }) {
  const id = useId();

  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1.5 block font-mono text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400"
      >
        {label}
      </label>
      <div className="relative">
        <Icon aria-hidden="true" className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
        <input id={id} required className={INPUT} {...props} />
      </div>
      {hint && <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  );
}

const fade = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.2 },
};

export function LoginPage() {
  const { status, login, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const [view, setView] = useState<View>(sessionExpired ? "sign_in" : "options");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);

  if (status === "authenticated" && !success) return <Navigate to="/" replace />;

  const go = (next: View) => {
    setView(next);
    setError(null);
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      if (view === "sign_up") await api.register({ name, email, password });
      await login(email, password);
      setSuccess(true);
      setTimeout(() => navigate("/", { replace: true }), 600);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const signUp = view === "sign_up";

  return (
    <div className="relative flex min-h-screen w-full select-none flex-col items-center justify-center overflow-hidden bg-slate-50 px-4 transition-colors duration-200 dark:bg-slate-950">
      <div className="absolute right-4 top-4 z-50">
        <ThemeToggle floating />
      </div>
      <FloatingBadges />

      <motion.main
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md rounded-2xl border border-slate-100 bg-white p-8 text-center shadow-xl shadow-slate-100/80 transition-all duration-200 md:p-10 dark:border-slate-800 dark:bg-slate-900 dark:shadow-slate-950/40"
      >
        <div className="mb-5 flex justify-center">
          <LoginLogo />
        </div>
        <h1 className="mb-2 font-display text-4xl font-bold tracking-tight text-slate-800 dark:text-white">
          CogniSeek
        </h1>
        <p className="mb-6 text-xs text-slate-500 dark:text-slate-400">
          One search across your local files, Google Drive and GitHub.
        </p>

        {sessionExpired && !error && view !== "options" && (
          <p
            role="status"
            className="mb-4 rounded-lg border border-amber-100 bg-amber-50 p-3 text-xs text-amber-900"
          >
            Your session has expired. Please log in again.
          </p>
        )}

        <AnimatePresence mode="wait">
          {view === "options" ? (
            <motion.div key="options" {...fade} className="space-y-3.5">
              <button
                type="button"
                onClick={() => go("sign_in")}
                className="w-full cursor-pointer rounded-xl border border-slate-200/55 bg-slate-50 py-3 text-sm font-semibold text-slate-800 transition-all duration-200 hover:bg-slate-100 active:scale-98 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                Sign In with Email
              </button>
              <div className="mt-4 border-t border-slate-100 pt-4 dark:border-slate-800">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Don&apos;t have an account?{" "}
                  <button
                    type="button"
                    onClick={() => go("sign_up")}
                    className="font-semibold text-blue-700 hover:underline dark:text-blue-400"
                  >
                    Create Account
                  </button>
                </p>
              </div>
            </motion.div>
          ) : (
            <motion.div key={view} {...fade} className="text-left">
              <div className="mb-4 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => go("options")}
                  aria-label="Back"
                  className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                >
                  <ArrowLeft aria-hidden="true" className="h-4 w-4" />
                </button>
                <h2 className="text-lg font-bold text-slate-800 dark:text-white">
                  {signUp ? "Create Account" : "Sign In"}
                </h2>
              </div>

              {success ? (
                <div role="status" className="flex flex-col items-center justify-center py-6 text-center">
                  <motion.div
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-600 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-400"
                  >
                    <CheckCircle2 aria-hidden="true" className="h-6 w-6" />
                  </motion.div>
                  <p className="text-sm font-semibold text-slate-800 dark:text-white">
                    {signUp ? "Account Created Successfully!" : "Successfully Authenticated"}
                  </p>
                </div>
              ) : (
                <form onSubmit={(e) => void onSubmit(e)} className="space-y-4">
                  {signUp && (
                    <Field
                      label="Full Name"
                      icon={User}
                      autoComplete="name"
                      placeholder="John Doe"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  )}
                  <Field
                    label="Email"
                    icon={Mail}
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <Field
                    label="Password"
                    icon={Lock}
                    type="password"
                    autoComplete={signUp ? "new-password" : "current-password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    hint={signUp ? "8–128 characters, with at least one letter and one digit." : undefined}
                  />

                  {error && (
                    <div
                      role="alert"
                      className="rounded-lg border border-red-100 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-400"
                    >
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={busy}
                    className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 text-sm font-semibold text-white shadow-xs transition-all duration-200 hover:bg-blue-700 active:scale-98 disabled:bg-slate-200 disabled:text-slate-700"
                  >
                    {busy
                      ? signUp
                        ? "Creating account..."
                        : "Authenticating..."
                      : signUp
                        ? "Create Account"
                        : "Sign In"}
                  </button>

                  <p className="pt-2 text-center text-xs text-slate-500 dark:text-slate-400">
                    {signUp ? "Already have an account?" : "Don't have an account?"}{" "}
                    <button
                      type="button"
                      onClick={() => go(signUp ? "sign_in" : "sign_up")}
                      className="font-semibold text-blue-700 hover:underline dark:text-blue-400"
                    >
                      {signUp ? "Sign In" : "Create Account"}
                    </button>
                  </p>
                </form>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.main>
    </div>
  );
}
