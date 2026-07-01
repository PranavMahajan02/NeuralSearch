import React, { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Platform, PlatformId, DashboardStats, IndexLog, AuthUser } from "./types";
import { MOCK_FILES } from "./data/mockFiles";
import PageLogin from "./components/PageLogin";
import PageConnection from "./components/PageConnection";
import PageChooseFirst from "./components/PageChooseFirst";
import PageIndexingCenter from "./components/PageIndexingCenter";
import PageDashboard from "./components/PageDashboard";
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
    name: "GitHub Repositories",
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

  // Priority platform, stream log feed and counts ref
  const [priorityPlatformId, setPriorityPlatformId] = useState<PlatformId | null>(null);
  const [streamFeed, setStreamFeed] = useState<IndexLog[]>([]);
  const indexedFileCountsRef = useRef<Record<PlatformId, number>>({
    google_drive: 0,
    google_photos: 0,
    github: 0,
    local_storage: 0
  });

  // Central sequential indexing engine
  useEffect(() => {
    // Find if there is any platform currently indexing
    const activePlatform = platforms.find((p) => p.connected && p.status === "indexing");
    if (!activePlatform) return;

    const platformId = activePlatform.id;

    // Filter potential files to index from MOCK_FILES
    let platformMockFiles = MOCK_FILES.filter((f) => f.platform === platformId);
    if (platformId === "local_storage") {
      const selected = activePlatform.selectedFolders || [];
      platformMockFiles = platformMockFiles.filter((f) => {
        if (!f.folder) return false;
        if (selected.length === 0) return false;
        return selected.some((sel) => {
          const normSel = sel.toLowerCase();
          const normFolder = f.folder!.toLowerCase();
          if (normSel.includes("desktop") && normFolder === "desktop") return true;
          if (normSel.includes("document") && normFolder === "documents") return true;
          if (normSel.includes("download") && normFolder === "downloads") return true;
          if (normSel.includes("picture") && normFolder === "pictures") return true;
          if (normSel.includes("video") && normFolder === "videos") return true;
          if (normFolder === "custom folder" && !["desktop", "documents", "downloads", "pictures", "videos"].some(k => normSel.includes(k))) return true;
          return normSel.includes(normFolder) || normFolder.includes(normSel);
        });
      });
    }

    const interval = setInterval(() => {
      // Re-read current platform status from the state to handle pause correctly
      setPlatforms((prevPlatforms) => {
        const currentP = prevPlatforms.find((p) => p.id === platformId);
        if (!currentP || currentP.status === "paused") {
          return prevPlatforms;
        }

        const nextProgress = Math.min(100, currentP.progress + Math.floor(Math.random() * 8) + 4);
        const filesIndexCount = indexedFileCountsRef.current[platformId];

        // Should we feed a log item?
        if (platformMockFiles.length > 0 && nextProgress > (filesIndexCount / platformMockFiles.length) * 100) {
          const fileToFeed = platformMockFiles[filesIndexCount];
          if (fileToFeed) {
            const newLogItem: IndexLog = {
              id: `${platformId}_log_${Date.now()}_${filesIndexCount}`,
              fileName: fileToFeed.name,
              platform: platformId,
              status: "processing",
              timestamp: new Date().toLocaleTimeString(),
              type: fileToFeed.type
            };

            setStreamFeed((prevFeed) => [newLogItem, ...prevFeed.slice(0, 15)]);
            indexedFileCountsRef.current[platformId] += 1;

            // Increment detailed stats
            setStats((prevStats) => {
              const updated = { ...prevStats };
              updated.indexedFiles += 1;
              if (fileToFeed.type === "image") {
                updated.indexedImages += 1;
              } else if (fileToFeed.type === "audio") {
                updated.indexedAudio += 1;
              } else if (fileToFeed.type === "video") {
                updated.indexedVideos += 1;
              }
              updated.storageUsageGbs = Math.round((updated.storageUsageGbs + 0.1) * 10) / 10;
              return updated;
            });
          }
        }

        // Check if finished
        if (nextProgress >= 100) {
          clearInterval(interval);

          // Add to indexed list
          setIndexedPlatforms((prevIndexed) => {
            if (!prevIndexed.includes(platformId)) {
              const nextIndexed = [...prevIndexed, platformId];

              // Increment platformsReady, lastSyncTime
              setStats((prevStats) => ({
                ...prevStats,
                platformsReady: nextIndexed.length,
                lastSyncTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              }));

              return nextIndexed;
            }
            return prevIndexed;
          });

          // Move the next waiting platform (if any) to indexing
          setTimeout(() => {
            setPlatforms((latestPlatforms) => {
              const updated = latestPlatforms.map((p) => {
                if (p.id === platformId) {
                  return { ...p, status: "indexed" as const, progress: 100, indexed: true };
                }
                return p;
              });

              const nextQueued = updated.find((p) => p.connected && p.status === "waiting");
              if (nextQueued) {
                return updated.map((p) => {
                  if (p.id === nextQueued.id) {
                    return { ...p, status: "indexing" as const, progress: 2 };
                  }
                  return p;
                });
              }
              return updated;
            });
          }, 1000);

          return prevPlatforms.map((p) => {
            if (p.id === platformId) {
              return { ...p, status: "indexed" as const, progress: 100, indexed: true };
            }
            return p;
          });
        }

        // Just update progress
        return prevPlatforms.map((p) => {
          if (p.id === platformId) {
            return { ...p, progress: nextProgress };
          }
          return p;
        });
      });

    }, 1500);

    return () => {
      clearInterval(interval);
    };
  }, [platforms]);

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

  const handleStartIndexing = (priorityId: PlatformId) => {
    setPriorityPlatformId(priorityId);
    // Flag priority resource as active indexing, set others connected as queued waiting
    setPlatforms((prev) =>
      prev.map((p) => {
        if (p.id === priorityId) {
          return { ...p, status: "indexing", progress: 2 };
        } else if (p.connected && p.status === "idle") {
          return { ...p, status: "waiting" };
        }
        return p;
      })
    );
    setCurrentPage("indexing_first");
  };

  const handleLogout = () => {
    authLogout();
    setUser(null);
    setAuthStatus("unauthenticated");

    // Reset to defaults
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
      setCurrentPage("connection");
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
                setCurrentPage("connection");
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