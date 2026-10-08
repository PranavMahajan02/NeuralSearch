import { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { motion } from "motion/react";
import {
  ChevronLeft,
  ChevronRight,
  Database,
  LayoutDashboard,
  LogOut,
  Menu,
  RefreshCw,
  Settings,
} from "lucide-react";

import { useConnectionCount, useJobs, useStats } from "../../api/queries";
import { PLATFORMS, isActiveJob } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { PlatformLogo } from "../common/Badges";
import { LogoTile, ThemeToggle } from "../common/Brand";
import { ConnectionBanner } from "../common/ConnectionBanner";
import { Modal } from "../common/Modal";
import { AccountDialog } from "./AccountDialog";

const NAV = [
  { to: "/search", label: "Dashboard", icon: LayoutDashboard },
  { to: "/platforms", label: "Platforms", icon: Database },
  { to: "/indexing", label: "Indexing Center", icon: RefreshCw },
];

const TITLES: Record<string, string> = {
  "/search": "Unified Search Command",
  "/platforms": "Integrations Cabinet",
  "/indexing": "Indexing Operations Office",
};

function NavItems({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const jobs = useJobs();
  const active = jobs.data?.filter(isActiveJob).length ?? 0;

  return (
    <ul className="space-y-1">
      {NAV.map(({ to, label, icon: Icon }) => (
        <li key={to}>
          <NavLink
            to={to}
            onClick={onNavigate}
            aria-label={collapsed ? label : undefined}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              `flex w-full items-center gap-3.5 rounded-xl px-3 py-2.5 text-xs font-semibold tracking-wide transition-all ${
                isActive
                  ? "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-800/40 dark:hover:text-slate-200"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  aria-hidden="true"
                  className={`h-4 w-4 shrink-0 ${isActive ? "text-blue-600 dark:text-blue-400" : "text-slate-500"}`}
                />
                {!collapsed && <span className="flex-1 truncate">{label}</span>}
                {to === "/indexing" && active > 0 && (
                  <span className="rounded-full bg-blue-600 px-2 py-0.5 text-[10px] font-bold text-white">
                    {collapsed ? active : `${active} active`}
                  </span>
                )}
              </>
            )}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

function UserCard({ collapsed = false }: { collapsed?: boolean }) {
  const { user, logout } = useAuth();
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="border-t border-slate-200 p-3 dark:border-slate-800/60">
      <div className={`flex items-center gap-3 rounded-xl p-2 ${collapsed ? "flex-col" : ""}`}>
        <div
          aria-hidden="true"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
        >
          {user?.name?.charAt(0).toUpperCase() || "U"}
        </div>
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <span className="block truncate text-xs font-bold text-slate-700 dark:text-slate-200">
              {user?.name}
            </span>
            <span className="block truncate text-[10px] text-slate-500 dark:text-slate-400">
              {user?.email}
            </span>
          </div>
        )}
        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          aria-label="Account settings"
          title="Account settings"
          className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        >
          <Settings aria-hidden="true" className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => void logout()}
          aria-label="Log out"
          title="Log out"
          className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        >
          <LogOut aria-hidden="true" className="h-4 w-4" />
        </button>
      </div>
      {settingsOpen && <AccountDialog onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}

/** "Portals Search Ready · N / 3 Connected": the single connection count (useConnectionCount). */
function ConnectionPill() {
  const stats = useStats();
  const { connected, supported } = useConnectionCount();
  const connectedPlatforms = PLATFORMS.filter((p) => stats.data?.platforms[p]?.connected);

  return (
    <Link
      to="/indexing"
      title="Open the Indexing Center"
      data-testid="connection-count"
      className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-1.5 transition-all hover:border-slate-300 hover:shadow-2xs dark:border-slate-800 dark:bg-slate-900/60 dark:hover:border-slate-700"
    >
      {connectedPlatforms.length > 0 && (
        <span className="hidden -space-x-1 pl-1 sm:flex">
          {connectedPlatforms.map((p) => (
            <span
              key={p}
              className="flex h-5 w-5 items-center justify-center rounded-full border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800"
            >
              <PlatformLogo platform={p} className="h-3 w-3" />
            </span>
          ))}
        </span>
      )}
      <span className="px-1.5 text-right sm:border-l sm:border-slate-200 dark:sm:border-slate-800">
        <span className="hidden font-mono text-[10px] leading-tight text-slate-500 sm:block dark:text-slate-400">
          Portals Search Ready
        </span>
        <span className="block text-xs font-bold text-slate-700 dark:text-slate-300">
          <span aria-hidden="true">🟢 </span>
          {connected} / {supported} Connected
        </span>
      </span>
    </Link>
  );
}

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const title = TITLES[location.pathname] ?? "CogniSeek";

  return (
    <div className="flex min-h-screen w-full bg-slate-50 transition-colors duration-200 dark:bg-[#070b13]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>

      <motion.aside
        animate={{ width: collapsed ? 68 : 250 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-y-0 left-0 z-30 hidden flex-col justify-between border-r border-slate-200 bg-white shadow-sm transition-colors duration-200 md:flex dark:border-slate-800/80 dark:bg-slate-900"
      >
        <div>
          <div className="flex items-center justify-between border-b border-slate-100 p-4 dark:border-slate-800/60">
            {!collapsed && (
              <div className="flex items-center gap-2">
                <LogoTile />
                <span className="font-display text-base font-bold leading-none tracking-tight text-slate-800 dark:text-slate-100">
                  CogniSeek
                </span>
              </div>
            )}
            <button
              type="button"
              onClick={() => setCollapsed((c) => !c)}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              className="mx-auto rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>
          <nav aria-label="Main" className="p-3">
            <NavItems collapsed={collapsed} />
          </nav>
        </div>
        <UserCard collapsed={collapsed} />
      </motion.aside>

      {drawerOpen && (
        <Modal title="Menu" variant="drawer" onClose={() => setDrawerOpen(false)}>
          <nav aria-label="Main">
            <NavItems onNavigate={() => setDrawerOpen(false)} />
          </nav>
          <div className="-mx-5 mt-6">
            <UserCard />
          </div>
        </Modal>
      )}

      <div
        className={`flex min-h-screen w-full min-w-0 flex-col transition-all duration-300 ${collapsed ? "md:pl-[68px]" : "md:pl-[250px]"}`}
      >
        <ConnectionBanner />
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-slate-200/80 bg-white/95 px-4 backdrop-blur-md transition-colors duration-200 sm:px-6 dark:border-slate-800/80 dark:bg-[#0f172a]/95">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              aria-label="Open menu"
              className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 md:hidden dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Menu aria-hidden="true" className="h-5 w-5" />
            </button>
            <h1 className="truncate font-display text-sm font-bold text-slate-800 dark:text-slate-100">
              {title}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <ConnectionPill />
            <ThemeToggle />
          </div>
        </header>
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-7xl flex-1 p-4 outline-none sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
