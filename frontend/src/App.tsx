import React, { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Platform, PlatformId, DashboardStats, IndexLog, AuthUser } from "./types";
import { MOCK_FILES } from "./data/mockFiles";
import PageLogin from "./components/PageLogin";
import PageConnection from "./components/PageConnection";
import PageChooseFirst from "./components/PageChooseFirst";
import PageIndexingCenter from "./components/PageIndexingCenter";
import PageDashboard from "./components/PageDashboard";
import { startIndexing } from "./services/index";
import { getDashboardStats } from "./services/dashboard";
import { getLoginState } from "./services/loginState";
import { getIndexJobs } from "./services/indexStatus";
import { getFolders } from "./services/localStorage";
import {
  connectGoogleDrive,
  disconnectGoogleDrive,
  getGoogleDriveStatus
} from "./services/googleDrive";
import {
  connectGithub,
  disconnectGithub,
  getGithubStatus
} from "./services/github";
import {
  isLoggedIn,
  getProfile,
  logout as authLogout
} from "./services/auth";
const INITIAL_PLATFORMS: Platform[] = [
  {
    id: "google_drive",
    name: "Google Drive",
    connected: false,
    indexed: false,
    status: "idle",
    progress: 0,
    iconName: "drive",
    color: "text-blue-500",
  },
  {
    id: "google_photos",
    name: "Google Photos",
    connected: false,
    indexed: false,
    status: "idle",
    progress: 0,
    iconName: "photos",
    color: "text-emerald-500",
  },
  {
    id: "github",
    name: "GitHub",
    connected: false,
    indexed: false,
    status: "idle",
    progress: 0,
    iconName: "github",
    color: "text-slate-800",
  },
  {
    id: "local_storage",
    name: "Local Storage",
    connected: false,
    indexed: false,
    status: "idle",
    progress: 0,
    iconName: "local",
    color: "text-indigo-505 text-indigo-500",
  },
];

type AppJourneyState =
  | "login"
  | "connection"
  | "choose_first"
  | "indexing_first"
  | "dashboard";

export default function App() {
  const [currentPage, setCurrentPage] = useState<AppJourneyState>("login");
  const [authStatus, setAuthStatus] = useState<
    "checking" | "authenticated" | "unauthenticated"
  >("checking");

  const [user, setUser] = useState<AuthUser | null>(null);
  const [platforms, setPlatforms] = useState<Platform[]>(INITIAL_PLATFORMS);
  const [indexedPlatforms, setIndexedPlatforms] = useState<string[]>([]);
  const [indexingState, setIndexingState] = useState({

    active: false,

    platform: "",

    progress: 0,

    status: "idle"

  });

  // Priority platform, stream log feed and counts ref
  const [priorityPlatformId, setPriorityPlatformId] = useState<PlatformId | null>(null);
  const [streamFeed, setStreamFeed] = useState<IndexLog[]>([]);
  const [indexJobs, setIndexJobs] = useState<any[]>([]);
  const indexedFileCountsRef = useRef<Record<PlatformId, number>>({
    google_drive: 0,
    google_photos: 0,
    github: 0,
    local_storage: 0
  });



  // Theme state: "light" or "dark"
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("cogniseek_theme");
      if (saved === "light" || saved === "dark") {
        return saved;
      }
    }
    return "light";
  });

  useEffect(() => {
    localStorage.setItem("cogniseek_theme", theme);
    const root = window.document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  // Storage usage stats and indices counts tracker
  const [stats, setStats] = useState<DashboardStats>({
    connectedPlatforms: 0,
    indexedFiles: 0,
    indexedImages: 0,
    indexedAudio: 0,
    indexedVideos: 0,
    platformsReady: 0,
    lastSyncTime: "",
    totalSearches: 0,
    storageUsageGbs: 0.0,
  });

  // Automatically keep KPI values in sync with the platform connections state
  useEffect(() => {
    const connectedCount = platforms.filter((p) => p.connected).length;
    setStats((prev) => ({
      ...prev,
      connectedPlatforms: connectedCount,
      platformsReady: indexedPlatforms.length,
    }));
  }, [platforms, indexedPlatforms]);

  // Handle connection toggling
  const handleTogglePlatformConnect = async (id: string) => {

    // Google Drive uses the backend API
    if (id === "google_drive") {

      try {

        const googlePlatform = platforms.find(
          (p) => p.id === "google_drive"
        );

        if (googlePlatform?.connected) {

          await disconnectGoogleDrive();

          setPlatforms((prev) =>
            prev.map((p) =>
              p.id === "google_drive"
                ? {
                  ...p,
                  connected: false,
                  status: "idle",
                  progress: 0
                }
                : p
            )
          );

        } else {

          await connectGoogleDrive();

          setPlatforms((prev) =>
            prev.map((p) =>
              p.id === "google_drive"
                ? {
                  ...p,
                  connected: true,
                  status: "waiting",
                  progress: 0
                }
                : p
            )
          );

        }

      } catch (error) {

        console.error(error);

        alert("Unable to connect Google Drive.");

      }

      return;
    }

    // GitHub uses the backend API
    if (id === "github") {

      try {

        const githubPlatform = platforms.find(
          (p) => p.id === "github"
        );

        if (githubPlatform?.connected) {

          await disconnectGithub();

          setPlatforms((prev) =>
            prev.map((p) =>
              p.id === "github"
                ? {
                  ...p,
                  connected: false,
                  status: "idle",
                  progress: 0
                }
                : p
            )
          );

        } else {

          await connectGithub();

          setPlatforms((prev) =>
            prev.map((p) =>
              p.id === "github"
                ? {
                  ...p,
                  connected: true,
                  status: "waiting",
                  progress: 0
                }
                : p
            )
          );

        }

      } catch (error) {

        console.error(error);

        alert("Unable to connect GitHub.");

      }

      return;
    }

    // Existing logic for every other platform
    setPlatforms((prev) =>
      prev.map((p) => {

        if (p.id === id) {

          const nextConnected = !p.connected;

          return {
            ...p,
            connected: nextConnected,
            status: nextConnected ? "waiting" : "idle",
            progress: 0
          };

        }

        return p;

      })
    );

  };

  const handleStartIndexing = async (
    priorityId: PlatformId,
    fromDashboard = false
  ) => {

    setPriorityPlatformId(priorityId);

    const connectedPlatforms = fromDashboard
      ? [
        priorityId === "local_storage"
          ? "local"
          : priorityId
      ]
      : platforms
        .filter((p) => p.connected)
        .map((p) => {
          if (p.id === "local_storage") return "local";
          return p.id;
        });

    const backendPriority =
      priorityId === "local_storage"
        ? "local"
        : priorityId;

    try {

      await startIndexing(
        backendPriority,
        connectedPlatforms
      );

      if (!fromDashboard) {

        setCurrentPage("indexing_first");

      }

    } catch (e) {

      console.error(e);

      alert("Unable to start indexing.");

    }

  };


  const handleLogout = async () => {

    await authLogout();

    setUser(null);
    setAuthStatus("unauthenticated");

    setPlatforms(INITIAL_PLATFORMS);
    setIndexedPlatforms([]);
    setPriorityPlatformId(null);
    setStreamFeed([]);

    indexedFileCountsRef.current = {
      google_drive: 0,
      google_photos: 0,
      github: 0,
      local_storage: 0
    };

    setStats({
      connectedPlatforms: 0,
      indexedFiles: 0,
      indexedImages: 0,
      indexedAudio: 0,
      indexedVideos: 0,
      platformsReady: 0,
      lastSyncTime: "",
      totalSearches: 0,
      storageUsageGbs: 0.0,
    });

    setCurrentPage("login");

  };

  const checkAuthentication = async () => {
    if (!isLoggedIn()) {
      setAuthStatus("unauthenticated");
      return;
    }

    try {
      const profile = await getProfile();
      setUser(profile);

      setAuthStatus("authenticated");

      const state = await getLoginState();

      if (state.has_indexed) {

        setCurrentPage("dashboard");

      }

      else {

        setCurrentPage("connection");

      }
    } catch (error) {
      authLogout();
      setUser(null);
      setAuthStatus("unauthenticated");
    }
  };
  useEffect(() => {
    checkAuthentication();
  }, []);

  useEffect(() => {

    if (
      currentPage !== "indexing_first" &&
      currentPage !== "dashboard"
    ) {
      return;
    }

    const interval = setInterval(async () => {
      try {

        const jobs = await getIndexJobs();
        setIndexJobs(jobs);

        setPlatforms(prev =>
          prev.map(platform => {

            const backendName =
              platform.id === "local_storage"
                ? "local"
                : platform.id;

            const job = jobs.find(
              (j: any) => j.platform === backendName
            );

            if (!job) {
              return platform;
            }

            if (job.status === "indexing") {

              setIndexingState({

                active: true,

                platform: backendName,

                progress: job.progress,

                status: "indexing"

              });

              return {

                ...platform,

                status: "indexing",

                progress: job.progress

              };

            }

            if (job.status === "completed") {
              setIndexingState({

                active: false,

                platform: backendName,

                progress: job.progress,

                status: "completed"

              });

              return {
                ...platform,
                status: "indexed",
                progress: job.progress,
                indexed: true
              };

            }

            return platform;

          })
        );

        const completed = jobs
          .filter((j: any) => j.status === "completed");

        // NEW
        setIndexedPlatforms(
          completed.map((j: any) =>
            j.platform === "local"
              ? "local_storage"
              : j.platform
          )
        );

        if (
          completed.length > 0 &&
          completed[0].platform ===
          (priorityPlatformId === "local_storage"
            ? "local"
            : priorityPlatformId)
        ) {

          const dashboard = await getDashboardStats();

          setStats(prev => ({
            ...prev,
            indexedFiles: dashboard.total_files,
            indexedImages: dashboard.images,
            indexedAudio: dashboard.audio,
            indexedVideos: dashboard.video,
            connectedPlatforms: dashboard.connected_platforms,
            platformsReady: dashboard.ready_platforms
          }));

          setCurrentPage("dashboard");


        }

      } catch (err) {

        console.error("Polling failed:", err);

      }

    }, 1000);

    return () => clearInterval(interval);

  }, [currentPage, priorityPlatformId]);

  useEffect(() => {

    if (authStatus !== "authenticated") {
      return;
    }

    async function restoreConnections() {

      // Restore Google Drive
      try {

        const status = await getGoogleDriveStatus();

        setPlatforms((prev) =>
          prev.map((p) =>
            p.id === "google_drive"
              ? {
                ...p,
                connected: status.connected,
                status: status.connected ? "waiting" : "idle"
              }
              : p
          )
        );

      } catch (error) {

        console.error(error);

      }

      // Restore GitHub
      try {

        const github = await getGithubStatus();

        setPlatforms((prev) =>
          prev.map((p) =>
            p.id === "github"
              ? {
                ...p,
                connected: github.connected,
                status: github.connected ? "waiting" : "idle"
              }
              : p
          )
        );

      } catch (error) {

        console.error(error);

      }

      // Restore Local Storage

      try {

        const folders = await getFolders();

        setPlatforms(prev =>
          prev.map(p =>
            p.id === "local_storage"
              ? {
                ...p,
                connected: folders.folders.length > 0,
                status:
                  folders.folders.length > 0
                    ? "waiting"
                    : "idle",
                selectedFolders: folders.folders
              }
              : p
          )
        );

      } catch (error) {

        console.error(error);

      }

      try {

        const dashboard = await getDashboardStats();

        setStats(prev => ({
          ...prev,
          connectedPlatforms: dashboard.connected_platforms,
          indexedFiles: dashboard.total_files,
          indexedImages: dashboard.images,
          indexedAudio: dashboard.audio,
          indexedVideos: dashboard.video,
          platformsReady: dashboard.ready_platforms
        }));

      } catch (error) {

        console.error(error);

      }

      try {

        const jobs = await getIndexJobs();

        setIndexJobs(jobs);

        const ready: string[] = [];

        jobs.forEach((job: any) => {

          if (job.status === "completed") {

            if (job.platform === "local") {

              ready.push("local_storage");

            } else {

              ready.push(job.platform);

            }

          }

        });

        setIndexedPlatforms(ready);

      } catch (err) {

        console.error("Polling failed:", err);


      }

    }

    restoreConnections();

  }, [authStatus]);

  if (authStatus === "checking") {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          fontSize: "22px",
          fontWeight: "600"
        }}
      >
        Checking authentication...
      </div>
    );
  }

  return (
    <div className={`min-h-screen transition-colors duration-200 ${theme === "dark" ? "dark bg-slate-950 text-slate-100" : "bg-slate-50 text-slate-800"} antialiased selection:bg-blue-100 selection:text-blue-900`}>
      <AnimatePresence mode="wait">
        {authStatus === "unauthenticated" && (
          <motion.div
            key="login_view"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <PageLogin
              onLoginSuccess={async () => {

                const profile = await getProfile();

                setUser(profile);

                setAuthStatus("authenticated");

                const state = await getLoginState();

                if (state.has_indexed) {

                  setCurrentPage("dashboard");

                }

                else {

                  setCurrentPage("connection");

                }

              }}
              theme={theme}
              onToggleTheme={toggleTheme}
            />
          </motion.div>
        )}

        {currentPage === "connection" && (
          <motion.div
            key="connection_view"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.4 }}
          >
            <PageConnection
              platforms={platforms}
              onToggleConnect={handleTogglePlatformConnect}
              onUpdatePlatforms={setPlatforms}
              onStartIndexing={handleStartIndexing}
              onNext={() => setCurrentPage("choose_first")}
              theme={theme}
              onToggleTheme={toggleTheme}
            />
          </motion.div>
        )}

        {currentPage === "choose_first" && (
          <motion.div
            key="choose_first_view"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.4 }}
          >
            <PageChooseFirst
              platforms={platforms}
              onStartIndexing={handleStartIndexing}
              onBack={() => setCurrentPage("connection")}
              theme={theme}
              onToggleTheme={toggleTheme}
            />
          </motion.div>
        )}

        {currentPage === "indexing_first" && (
          <motion.div
            key="indexing_first_view"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.4 }}
          >
            <PageIndexingCenter
              isOnboarding={true}
              platforms={platforms}
              onUpdatePlatforms={setPlatforms}
              indexedPlatforms={indexedPlatforms}
              onUpdateIndexedPlatforms={setIndexedPlatforms}
              stats={stats}
              onUpdateStats={setStats}
              onEnterDashboard={() => setCurrentPage("dashboard")}
              theme={theme}
              onToggleTheme={toggleTheme}
              streamFeed={streamFeed}
              priorityPlatformId={priorityPlatformId}
              indexJobs={indexJobs}
            />
          </motion.div>
        )}

        {currentPage === "dashboard" && (
          <motion.div
            key="dashboard_view"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <PageDashboard
              platforms={platforms}
              onUpdatePlatforms={setPlatforms}
              indexedPlatforms={indexedPlatforms}
              onUpdateIndexedPlatforms={setIndexedPlatforms}
              stats={stats}
              onUpdateStats={setStats}
              onLogout={handleLogout}
              onStartIndexing={handleStartIndexing}
              onTogglePlatformConnect={handleTogglePlatformConnect}
              indexingState={indexingState}
              theme={theme}
              onToggleTheme={toggleTheme}
              streamFeed={streamFeed}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}