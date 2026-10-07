import { motion } from "motion/react";
import { Moon, Search, Sun } from "lucide-react";

import { useThemeContext } from "../../hooks/useTheme";

/** Small gradient tile used in the sidebar. */
export function LogoTile({ size = "h-7 w-7" }: { size?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`${size} flex shrink-0 items-center justify-center rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 shadow-xs`}
    >
      <Search className="h-3.5 w-3.5 text-white" />
    </div>
  );
}

/** The login card's mark. */
export function LoginLogo() {
  return (
    <div aria-hidden="true" className="relative flex h-14 w-14 select-none items-center justify-center">
      <div className="absolute inset-1 rounded-[18px] bg-blue-500/10 blur-md" />
      <div className="absolute inset-0 flex items-center justify-center rounded-[16px] border border-white/10 bg-gradient-to-tr from-blue-600 to-indigo-500 shadow-md shadow-blue-500/10">
        <div className="relative flex h-full w-full items-center justify-center overflow-hidden rounded-[14px] border border-white/5">
          <div className="absolute h-8 w-8 rounded-full border border-dashed border-white/15 opacity-60" />
          <div className="relative flex h-6.5 w-6.5 items-center justify-center rounded-lg border border-white/15 bg-white/10">
            <Search className="h-3.5 w-3.5 text-white" />
          </div>
        </div>
      </div>
    </div>
  );
}

/** The dashboard hero's orbiting lens logo. */
export function HeroLogo() {
  return (
    <motion.div
      aria-hidden="true"
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="relative mx-auto mb-6 flex h-20 w-20 select-none items-center justify-center"
    >
      <div className="absolute inset-2 animate-pulse rounded-[22px] bg-blue-500/15 blur-xl" />
      <div className="absolute inset-0 flex items-center justify-center rounded-[22px] border border-white/15 bg-gradient-to-tr from-blue-600 to-indigo-500 p-0.5 shadow-lg shadow-blue-500/15">
        <div className="relative flex h-full w-full items-center justify-center overflow-hidden rounded-[20px] border border-white/10">
          <div
            className="absolute inset-0 scale-135 animate-spin rounded-full border border-white/5 opacity-40"
            style={{ animationDuration: "24s" }}
          />
          <div className="absolute h-12 w-12 rounded-full border border-dashed border-white/10 opacity-30" />
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-white/20 bg-white/10 shadow-inner backdrop-blur-md">
            <Search className="h-4.5 w-4.5 text-white drop-shadow-sm" />
            <span className="absolute right-1 top-1 h-1 w-1 animate-ping rounded-full bg-cyan-300" />
            <span className="absolute right-1 top-1 h-1 w-1 rounded-full bg-cyan-300" />
          </div>
        </div>
      </div>
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 12, repeat: Infinity, ease: "linear" }}
        className="pointer-events-none absolute inset-0"
      >
        <span className="absolute left-1/2 top-0.5 h-2 w-2 -translate-x-1/2 rounded-full border border-white bg-indigo-300 shadow-xs" />
      </motion.div>
    </motion.div>
  );
}

/** The rounded theme toggle used in every page header. */
export function ThemeToggle({ floating = false }: { floating?: boolean }) {
  const { theme, toggle } = useThemeContext();
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      className={`flex cursor-pointer items-center justify-center rounded-xl border p-2.5 transition-all active:scale-95 ${
        floating
          ? "border-slate-200/60 bg-white/75 text-slate-600 shadow-xs backdrop-blur-md hover:text-slate-900 dark:border-slate-800/80 dark:bg-slate-900/75 dark:text-slate-300 dark:hover:text-white"
          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-800 dark:border-slate-800/80 dark:bg-slate-900/80 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-amber-400"
      }`}
    >
      {theme === "dark" ? (
        <Sun aria-hidden="true" className="h-4 w-4 text-amber-500" />
      ) : (
        <Moon aria-hidden="true" className="h-4 w-4 text-slate-600" />
      )}
    </button>
  );
}
