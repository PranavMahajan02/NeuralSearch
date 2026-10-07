import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Activity, LogOut, Menu, Moon, Plug, Search, Sun } from "lucide-react";

import { useConnectionCount, useJobs } from "../../api/queries";
import { isActiveJob } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { useTheme } from "../../hooks/useTheme";
import { ConnectionBanner } from "../common/ConnectionBanner";
import { Modal } from "../common/Modal";

const NAV = [
  { to: "/search", label: "Search", icon: Search },
  { to: "/platforms", label: "Platforms", icon: Plug },
  { to: "/indexing", label: "Indexing", icon: Activity },
];

const TITLES: Record<string, string> = {
  "/search": "Search",
  "/platforms": "Platforms",
  "/indexing": "Indexing",
};

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  const jobs = useJobs();
  const active = jobs.data?.filter(isActiveJob).length ?? 0;

  return (
    <ul className="space-y-1">
      {NAV.map(({ to, label, icon: Icon }) => (
        <li key={to}>
          <NavLink
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
                isActive
                  ? "bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-200"
                  : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`
            }
          >
            <Icon aria-hidden="true" className="h-4 w-4" />
            <span className="flex-1">{label}</span>
            {to === "/indexing" && active > 0 && (
              <span className="rounded-full bg-blue-700 px-2 text-xs text-white">{active} active</span>
            )}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

function SidebarFooter() {
  const { user, logout } = useAuth();
  const { connected, supported, isLoading } = useConnectionCount();

  return (
    <div className="space-y-3 border-t border-slate-200 p-4 text-sm dark:border-slate-800">
      <p className="text-slate-600 dark:text-slate-300" data-testid="connection-count">
        {isLoading ? "Platforms: …" : `Platforms connected: ${connected} / ${supported}`}
      </p>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-medium">{user?.name}</p>
          <p className="truncate text-xs text-slate-600 dark:text-slate-400">{user?.email}</p>
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          aria-label="Log out"
          className="rounded-md p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <LogOut aria-hidden="true" className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2 px-4 py-5">
      <img src="/favicon.svg" alt="" className="h-7 w-7" />
      <span className="text-lg font-bold tracking-tight">CogniSeek</span>
    </div>
  );
}

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const title = TITLES[location.pathname] ?? "CogniSeek";

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>

      <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white md:flex dark:border-slate-800 dark:bg-slate-900">
        <Brand />
        <nav aria-label="Main" className="flex-1 px-3">
          <NavItems />
        </nav>
        <SidebarFooter />
      </aside>

      {drawerOpen && (
        <Modal title="Menu" variant="drawer" onClose={() => setDrawerOpen(false)}>
          <nav aria-label="Main">
            <NavItems onNavigate={() => setDrawerOpen(false)} />
          </nav>
          <div className="-mx-5 mt-6">
            <SidebarFooter />
          </div>
        </Modal>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <ConnectionBanner />
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
            className="rounded-md p-2 hover:bg-slate-100 md:hidden dark:hover:bg-slate-800"
          >
            <Menu aria-hidden="true" className="h-5 w-5" />
          </button>
          <h1 className="flex-1 text-base font-semibold">{title}</h1>
          <button
            type="button"
            onClick={toggle}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            className="rounded-md p-2 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            {theme === "dark" ? (
              <Sun aria-hidden="true" className="h-5 w-5" />
            ) : (
              <Moon aria-hidden="true" className="h-5 w-5" />
            )}
          </button>
        </header>
        <main
          id="main"
          tabIndex={-1}
          className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 outline-none sm:px-6"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
