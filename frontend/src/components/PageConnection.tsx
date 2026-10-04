import React, { useRef, useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Platform } from "../types";
import { indexLocalStorage } from "../services/localStorage";
import {
  getFolders,
  addFolder,
  removeFolder,
  pickFolder
} from "../services/localStorage";
import {
  HardDrive,
  Image as ImageIcon,
  Github,
  Database,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Sun,
  Moon,
  Folder,
  Plus,
  X,
  Play,
  FolderPlus
} from "lucide-react";

interface PageConnectionProps {
  platforms: Platform[];
  onToggleConnect: (id: string) => void;
  onUpdatePlatforms: React.Dispatch<React.SetStateAction<Platform[]>>;
  onStartIndexing?: (id: string) => void;
  onNext: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export default function PageConnection({
  platforms,
  onToggleConnect,
  onUpdatePlatforms,
  onStartIndexing,
  onNext,
  theme,
  onToggleTheme
}: PageConnectionProps) {
  const [customPath, setCustomPath] = useState("");
  useEffect(() => {

    async function loadFolders() {

      try {

        const data = await getFolders();

        console.log(data);

        onUpdatePlatforms(prev =>
          prev.map(p =>
            p.id === "local_storage"
              ? {
                ...p,
                selectedFolders: data.folders,
                connected: data.folders.length > 0
              }
              : p
          )
        );

      } catch (error) {

        console.error(error);

      }

    }

    loadFolders();

  }, []);

  const handleClearFolders = async () => {

    const localPlatform = platforms.find(
      p => p.id === "local_storage"
    );

    if (!localPlatform?.selectedFolders?.length) return;

    try {

      for (const folder of localPlatform.selectedFolders) {
        await removeFolder(folder);
      }

      onUpdatePlatforms(prev =>
        prev.map(p =>
          p.id === "local_storage"
            ? {
              ...p,
              selectedFolders: []
            }
            : p
        )
      );

    } catch (error) {

      console.error(error);

      alert("Unable to clear folders.");

    }

  };

  const handleStartLocalIndexing = async () => {

    try {

      const result = await indexLocalStorage();

      console.log(result);

      if (onStartIndexing) {
        await onStartIndexing("local_storage");
      }

    } catch (error) {

      console.error("INDEX ERROR:", error);

      alert("Local Storage indexing failed.");

    }

  };

  const handleTriggerFolderPicker = async () => {

    try {

      const data = await pickFolder();

      if (!data.folder) {
        return;
      }

      const result = await addFolder(data.folder);

      onUpdatePlatforms(prev =>
        prev.map(p =>
          p.id === "local_storage"
            ? {
              ...p,
              selectedFolders: result.folders,
              connected: result.folders.length > 0
            }
            : p
        )
      );

    } catch (error) {

      console.error(error);

      alert("Unable to open native folder picker.");

    }

  };

  const handleAddCustomFolder = async (e?: React.FormEvent) => {

    if (e) e.preventDefault();

    if (!customPath.trim()) return;

    try {

      const data = await addFolder(customPath.trim());

      onUpdatePlatforms(prev =>
        prev.map(p =>
          p.id === "local_storage"
            ? {
              ...p,
              selectedFolders: data.folders
            }
            : p
        )
      );

      setCustomPath("");

    } catch (error) {

      console.error(error);

      alert("Unable to add folder.");

    }

  };

  const handleRemoveFolder = async (folder: string) => {

    try {

      const data = await removeFolder(folder);

      onUpdatePlatforms(prev =>
        prev.map(p =>
          p.id === "local_storage"
            ? {
              ...p,
              selectedFolders: data.folders
            }
            : p
        )
      );

    } catch (error) {

      console.error(error);

      alert("Unable to remove folder.");

    }

  };


  const renderPlatformIcon = (iconName: string, color: string) => {
    const sizeClasses = "w-6 h-6 " + color;
    switch (iconName) {
      case "drive":
        return <HardDrive className={sizeClasses} />;
      case "photos":
        return <ImageIcon className={sizeClasses} />;
      case "github":
        return <Github className={sizeClasses} />;
      case "local":
        return <Database className={sizeClasses} />;
      default:
        return <HardDrive className={sizeClasses} />;
    }
  };

  const localStoragePlatform = platforms.find((p) => p.id === "local_storage");
  const selectedFolders = localStoragePlatform?.selectedFolders || [];
  const someConnected = platforms.some((p) => p.connected);

  return (
    <div id="connection_page_wrapper" className="w-full min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col justify-between py-12 px-4 sm:px-6 md:px-8 transition-colors duration-200 relative">
      {/* Hidden input for folder picking */}

      {/* Absolute top-right Theme Switcher */}
      <div className="absolute top-4 right-4 z-50">
        <button
          id="theme_toggle_connection"
          onClick={onToggleTheme}
          className="p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800/80 bg-white/75 dark:bg-slate-900/75 backdrop-blur-md text-slate-600 dark:text-slate-350 hover:text-slate-900 dark:hover:text-white shadow-xs cursor-pointer active:scale-95 transition-all"
          title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {theme === "dark" ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-slate-600" />}
        </button>
      </div>

      {/* Header section */}
      <div className="max-w-4xl mx-auto w-full text-center mt-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 rounded-full text-xs font-semibold uppercase tracking-wider mb-4 border border-blue-100 dark:border-blue-900/50"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Step 2 of 4 • Set Up Integrations
        </motion.div>

        <h2 id="connection_title" className="font-display text-3xl sm:text-4xl font-bold text-slate-800 dark:text-white tracking-tight">
          Connect Your Platforms
        </h2>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
          Choose the platforms you want CogniSeek to index. You can search across all connected platforms simultaneously once indexed.
        </p>
      </div>

      {/* Grid of platforms */}
      <div className="max-w-4xl mx-auto w-full mt-10 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {platforms.map((platform, idx) => {
          const isLocalStorageConnected = platform.id === "local_storage" && platform.connected;
          return (
            <motion.div
              key={platform.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: idx * 0.05 }}
              id={`card_container_${platform.id}`}
              className={`bg-white dark:bg-slate-900 rounded-xl p-5 border transition-all duration-300 flex flex-col justify-between ${isLocalStorageConnected
                ? "col-span-1 sm:col-span-2 md:col-span-4 min-h-[22rem] h-auto"
                : "min-h-[11rem] h-44 col-span-1"
                } ${platform.connected
                  ? "border-blue-200 dark:border-blue-800/80 ring-2 ring-blue-500/10 shadow-xs"
                  : "border-slate-200/80 dark:border-slate-800/80 hover:border-slate-350 dark:hover:border-slate-705 hover:shadow-xs shadow-none"
                }`}
            >
              {isLocalStorageConnected ? (
                <div className="flex flex-col h-full gap-4">
                  <div className="flex justify-between items-start border-b border-slate-100 dark:border-slate-800/60 pb-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-100 dark:border-slate-850">
                        {renderPlatformIcon(platform.iconName, platform.color)}
                      </div>
                      <div>
                        <h3 className="font-display font-bold text-slate-800 dark:text-white text-base">
                          {platform.name}
                        </h3>
                        <p className="text-[11px] text-slate-400 dark:text-slate-500">
                          Configure directories to index and search. Excluded folders won't be scanned.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <motion.div
                        initial={{ scale: 0.7 }}
                        animate={{ scale: 1 }}
                        className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-100 dark:border-emerald-900/50 px-2 py-0.5 rounded-full text-[11px] font-semibold"
                      >
                        <CheckCircle2 className="w-3 h-3 text-emerald-650 dark:text-emerald-400 fill-emerald-100 dark:fill-emerald-950/20" />
                        Connected
                      </motion.div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                    {/* Left Panel: Picker triggers and custom path add */}
                    <div className="md:col-span-5 flex flex-col justify-between gap-5">
                      <div className="space-y-4">
                        <div>
                          <label className="block text-[10px] font-bold font-mono text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                            Folder Selection Options
                          </label>
                          <button
                            type="button"
                            onClick={handleTriggerFolderPicker}
                            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-xs cursor-pointer transition-all active:scale-98"
                          >
                            <Folder className="w-4 h-4" />
                            Browse Folders (Native Picker)
                          </button>
                        </div>

                        {/* Add custom folder path */}
                        <form onSubmit={handleAddCustomFolder}>
                          <label className="block text-[10px] font-bold font-mono text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1.5">
                            Add Custom Path manually
                          </label>
                          <div className="flex gap-2">
                            <input
                              type="text"
                              placeholder="e.g. D:\Research Paper"
                              value={customPath}
                              onChange={(e) => setCustomPath(e.target.value)}
                              className="flex-grow text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-xl p-2.5 font-mono text-slate-700 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                            />
                            <button
                              type="submit"
                              className="px-3 bg-slate-100 dark:bg-slate-850 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-xl transition-all cursor-pointer border border-slate-200 dark:border-slate-800 flex items-center justify-center"
                            >
                              <Plus className="w-4 h-4" />
                            </button>
                          </div>
                        </form>
                      </div>

                      {/* Main Action Bar */}
                      <div className="flex items-center gap-3 border-t border-slate-100 dark:border-slate-800/60 pt-4 mt-2">
                        <button
                          type="button"
                          onClick={() => onToggleConnect(platform.id)}
                          className="flex-grow py-2 px-3 rounded-xl text-xs font-semibold bg-red-50 dark:bg-red-950/20 text-red-650 dark:text-red-400 hover:bg-red-100/70 dark:hover:bg-red-950/40 cursor-pointer transition-all active:scale-97 text-center border border-red-100/50 dark:border-red-900/30"
                        >
                          Disconnect Storage
                        </button>
                        {onStartIndexing && (
                          <button
                            type="button"
                            disabled={selectedFolders.length === 0}
                            onClick={handleStartLocalIndexing}
                            className={`flex-grow flex items-center justify-center gap-1.5 py-2 px-4 rounded-xl text-xs font-semibold transition-all cursor-pointer active:scale-97 border ${selectedFolders.length > 0
                              ? "bg-emerald-600 hover:bg-emerald-700 text-white border-transparent shadow-xs"
                              : "bg-slate-100 dark:bg-slate-850 text-slate-400 dark:text-slate-650 border-slate-200 dark:border-slate-800 cursor-not-allowed"
                              }`}
                          >
                            <Play className="w-3.5 h-3.5 fill-current" />
                            Start Indexing
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Right Panel: Selected Directories View */}
                    <div className="md:col-span-7 bg-slate-50/50 dark:bg-slate-950/40 border border-slate-150/60 dark:border-slate-850 rounded-xl p-4 flex flex-col h-64 md:h-auto min-h-[14rem]">
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-[10px] font-bold font-mono text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                          Selected Directories ({selectedFolders.length})
                        </span>
                        {selectedFolders.length > 0 && (
                          <button
                            type="button"
                            onClick={handleClearFolders}
                            className="text-[10px] font-semibold text-red-500 hover:text-red-650 dark:hover:text-red-400 cursor-pointer hover:underline"
                          >
                            Clear All
                          </button>
                        )}
                      </div>

                      <div className="flex-grow overflow-y-auto pr-1 space-y-2 max-h-48">
                        <AnimatePresence initial={false}>
                          {selectedFolders.length === 0 ? (
                            <motion.div
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              exit={{ opacity: 0 }}
                              className="h-full flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900"
                            >
                              <FolderPlus className="w-8 h-8 text-slate-350 dark:text-slate-600 mb-2" />
                              <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                                No folders selected
                              </p>
                              <p className="text-[10px] text-slate-450 dark:text-slate-500 max-w-xs mt-1">
                                Click the browse button or type a custom path to add directories for indexing.
                              </p>
                            </motion.div>
                          ) : (
                            selectedFolders.map((folder) => (
                              <motion.div
                                key={folder}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 10 }}
                                className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xs hover:shadow-xs transition-shadow group"
                              >
                                <div className="flex items-center gap-2.5 min-w-0">
                                  <div className="p-1.5 bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-450 rounded-md">
                                    <Folder className="w-3.5 h-3.5" />
                                  </div>
                                  <span className="text-xs font-mono font-medium text-slate-700 dark:text-slate-350 truncate pr-2">
                                    {folder}
                                  </span>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => handleRemoveFolder(folder)}
                                  className="p-1 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 cursor-pointer transition-colors"
                                  title="Remove folder"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </motion.div>
                            ))
                          )}
                        </AnimatePresence>
                      </div>

                      {selectedFolders.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-slate-150/60 dark:border-slate-800/60 flex justify-end">
                          <button
                            type="button"
                            onClick={handleTriggerFolderPicker}
                            className="flex items-center gap-1 text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 cursor-pointer"
                          >
                            <Plus className="w-3 h-3" />
                            Add More Folders
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex justify-between items-start">
                    <div className="p-3 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-100 dark:border-slate-850">
                      {renderPlatformIcon(platform.iconName, platform.color)}
                    </div>
                    {platform.connected && (
                      <motion.div
                        initial={{ scale: 0.7 }}
                        animate={{ scale: 1 }}
                        className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-100 dark:border-emerald-900/50 px-2 py-0.5 rounded-full text-[11px] font-semibold"
                      >
                        <CheckCircle2 className="w-3 h-3 text-emerald-650 dark:text-emerald-400 fill-emerald-100 dark:fill-emerald-950/20" />
                        Connected
                      </motion.div>
                    )}
                  </div>

                  <div>

                    <h3 className="font-display font-bold text-slate-800 dark:text-white text-base mt-2">
                      {platform.name}
                    </h3>

                    {
                      platform.id === "google_photos" && (

                        <p className="mt-1 text-[11px] text-slate-400">
                          Available in a future update
                        </p>

                      )
                    }

                    {
                      platform.id === "google_photos" ? (

                        <button
                          disabled
                          className="mt-3 w-full py-2 px-3 rounded-lg text-xs font-semibold bg-gray-300 dark:bg-slate-700 text-gray-600 dark:text-slate-400 cursor-not-allowed"
                        >
                          Coming Soon
                        </button>

                      ) : (

                        <button
                          id={`btn_connect_${platform.id}`}
                          onClick={() => onToggleConnect(platform.id)}
                          className={`mt-3 w-full py-2 px-3 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer text-center ${platform.connected
                            ? "bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 active:scale-97"
                            : "bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-500 text-white shadow-xs active:scale-97"
                            }`}
                        >
                          {platform.connected ? "Disconnect" : "Connect"}
                        </button>

                      )
                    }

                  </div>
                </>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Dynamic Continue Button footer area */}
      <div className="max-w-4xl mx-auto w-full mt-12 flex justify-center mb-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-3 w-full max-w-sm"
        >
          <button
            id="btn_continue_to_indexing"
            disabled={!someConnected}
            onClick={onNext}
            className={`w-full py-3.5 px-6 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 shadow-md transition-all duration-300 cursor-pointer ${someConnected
              ? "bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-500 text-white shadow-blue-100 dark:shadow-none active:translate-y-[1px]"
              : "bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-600 cursor-not-allowed shadow-none"
              }`}
          >
            <span>Continue to Priority Indexing</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          {!someConnected ? (
            <p className="text-[11px] text-slate-400 dark:text-slate-500 animate-pulse text-center">
              Please connect at least one storage platform to continue.
            </p>
          ) : (
            <p className="text-[11px] text-slate-400 dark:text-slate-500 text-center">
              Great! You can connect more later in the Platforms List.
            </p>
          )}
        </motion.div>
      </div>
    </div>
  );
}
