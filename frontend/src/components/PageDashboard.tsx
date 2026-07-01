import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Platform, PlatformId, MockFile, DashboardStats, SearchType, IndexLog } from "../types";
import { searchFiles, MOCK_FILES } from "../data/mockFiles";
import PageIndexingCenter from "./PageIndexingCenter";
import {
  Search,
  LayoutDashboard,
  FileText,
  Image,
  Video,
  Database,
  RefreshCw,
  BarChart3,
  Settings,
  Menu,
  ChevronLeft,
  ChevronRight,
  HardDrive,
  Github,
  CheckCircle,
  AlertCircle,
  HelpCircle,
  Star,
  Clock,
  Eye,
  Trash2,
  Lock,
  Compass,
  ListFilter,
  CheckCircle2,
  Layers,
  ArrowUpRight,
  Share2,
  ChevronDown,
  Check,
  Sun,
  Moon,
  Link2,
  Music,
  FolderOpen,
  X,
  Play
} from "lucide-react";

interface PageDashboardProps {
  platforms: Platform[];
  onUpdatePlatforms: React.Dispatch<React.SetStateAction<Platform[]>>;
  indexedPlatforms: string[];
  onUpdateIndexedPlatforms: (indexed: string[]) => void;
  stats: DashboardStats;
  onUpdateStats: React.Dispatch<React.SetStateAction<DashboardStats>>;
  onLogout: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  streamFeed: IndexLog[];
}

export default function PageDashboard({
  platforms,
  onUpdatePlatforms,
  indexedPlatforms,
  onUpdateIndexedPlatforms,
  stats,
  onUpdateStats,
  onLogout,
  theme,
  onToggleTheme,
  streamFeed
}: PageDashboardProps) {
  // Sidebar states
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("dashboard");

  // Search filter states
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState<SearchType>("all");
  const [platformFilter, setPlatformFilter] = useState<string>("all");

  // Dropdown UI states for custom fully-rounded selective menus
  const [searchTypeOpen, setSearchTypeOpen] = useState(false);
  const [platformOpen, setPlatformOpen] = useState(false);

  const SEARCH_TYPES: { id: SearchType; label: string }[] = [
    { id: "all", label: "All Types" },
    { id: "document", label: "Documents" },
    { id: "image", label: "Images" },
    { id: "audio", label: "Audio" },
    { id: "video", label: "Video" }
  ];

  // Content suggestion tab state below search bar
  const [suggestionTab, setSuggestionTab] = useState<"recent" | "favorites" | "most_searched">("recent");



  // Active modal file for search result inspection
  const [activeModalFile, setActiveModalFile] = useState<MockFile | null>(null);

  // Platform icon visual mapping
  const renderPlatformLogo = (iconName: string, color: string, sizeClasses = "w-4 h-4") => {
    switch (iconName) {
      case "drive":
        return <HardDrive className={`${sizeClasses} ${color}`} />;
      case "photos":
        return <Image className={`${sizeClasses} ${color}`} />;
      case "github":
        return <Github className={`${sizeClasses} ${color}`} />;
      case "local":
        return <Database className={`${sizeClasses} ${color}`} />;
      default:
        return <HardDrive className={`${sizeClasses} ${color}`} />;
    }
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case "image":
        return <Image className="w-4 h-4 text-emerald-500" />;
      case "video":
        return <Play className="w-4 h-4 text-purple-500" />;
      case "audio":
        return <Music className="w-4 h-4 text-amber-500" />;
      default:
        return <FileText className="w-4 h-4 text-blue-500" />;
    }
  };

  // Perform search matching
  const localStoragePlatform = platforms.find((p) => p.id === "local_storage");
  const matchingResults = searchFiles(
    query,
    searchType,
    platformFilter,
    indexedPlatforms
  ).filter((f) => {
    if (f.platform === "local_storage") {
      const selected = localStoragePlatform?.selectedFolders || [];
      if (selected.length === 0) return false;
      return f.folder ? selected.some((sel) => {
        const normSel = sel.toLowerCase();
        const normFolder = f.folder!.toLowerCase();
        if (normSel.includes("desktop") && normFolder === "desktop") return true;
        if (normSel.includes("document") && normFolder === "documents") return true;
        if (normSel.includes("download") && normFolder === "downloads") return true;
        if (normSel.includes("picture") && normFolder === "pictures") return true;
        if (normSel.includes("video") && normFolder === "videos") return true;
        if (normFolder === "custom folder" && !["desktop", "documents", "downloads", "pictures", "videos"].some(k => normSel.includes(k))) return true;
        return normSel.includes(normFolder) || normFolder.includes(normSel);
      }) : true;
    }
    return true;
  });

  // Track search trigger statistics
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateStats({
      ...stats,
      totalSearches: stats.totalSearches + 1
    });
  };

  // Preset click triggers search parameter population
  const handlePresetSearch = (text: string, type: SearchType = "all", platform = "all") => {
    setQuery(text);
    setSearchType(type);
    setPlatformFilter(platform);
    onUpdateStats({
      ...stats,
      totalSearches: stats.totalSearches + 1
    });
  };

  const clearSearch = () => {
    setQuery("");
    setSearchType("all");
    setPlatformFilter("all");
  };

  // Quick navigation updates
  const handleSidebarTabClick = (tabId: string) => {
    setActiveTab(tabId);
    // Pre-apply filters if specific navigation tabs clicked
    if (tabId === "documents") {
      setSearchType("document");
      setActiveTab("dashboard");
    } else if (tabId === "images") {
      setSearchType("image");
      setActiveTab("dashboard");
    } else if (tabId === "audio") {
      setSearchType("audio");
      setActiveTab("dashboard");
    } else if (tabId === "video") {
      setSearchType("video");
      setActiveTab("dashboard");
    }
  };

  // Retrieve suggest block datasets
  const getSuggestionFiles = () => {
    switch (suggestionTab) {
      case "favorites":
        return MOCK_FILES.filter((f) => f.isFavorite && indexedPlatforms.includes(f.platform)).slice(0, 5);
      case "most_searched":
        return MOCK_FILES.filter((f) => f.searchCount && f.searchCount > 15 && indexedPlatforms.includes(f.platform)).slice(0, 5);
      case "recent":
      default:
        return MOCK_FILES.filter((f) => indexedPlatforms.includes(f.platform)).slice(0, 5);
    }
  };

  // Highlights search queries
  const renderHighlightedSnippet = (text: string, queryWord: string) => {
    if (!queryWord) return text;
    const regex = new RegExp(`(${escapeRegExp(queryWord)})`, "gi");
    const parts = text.split(regex);
    return (
      <>
        {parts.map((part, i) =>
          part.toLowerCase() === queryWord.toLowerCase() ? (
            <mark key={i} className="bg-blue-100 text-blue-800 rounded px-1 font-semibold">
              {part}
            </mark>
          ) : (
            part
          )
        )}
      </>
    );
  };

  const escapeRegExp = (string: string) => {
    return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  };

  return (
    <div id="full_dashboard_container" className="flex min-h-screen bg-slate-50 dark:bg-[#070b13] w-full transition-colors duration-200">

      {/* 1. Left Sidebar Navigation Panel */}
      <motion.aside
        id="saas_sidebar"
        animate={{ width: sidebarCollapsed ? "68px" : "250px" }}
        className="fixed inset-y-0 left-0 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800/80 z-30 flex flex-col justify-between shadow-sm transition-colors duration-200"
      >
        <div>
          {/* Header Area */}
          <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-slate-800/60">
            {!sidebarCollapsed && (
              <div className="flex items-center gap-2">
                <div className="relative w-7 h-7 shrink-0 flex items-center justify-center">
                  <div className="absolute inset-0 bg-gradient-to-tr from-blue-600 to-indigo-550 rounded-lg flex items-center justify-center shadow-xs">
                    <Search className="w-3.5 h-3.5 text-white" />
                  </div>
                </div>
                <h2 className="font-display font-bold text-slate-800 dark:text-slate-100 text-base leading-none tracking-tight">
                  CogniSeek
                </h2>
              </div>
            )}

            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-450 cursor-pointer mx-auto transition-colors"
            >
              {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>

          {/* Navigation Items */}
          <nav className="p-3 space-y-1">
            {[
              { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
              { id: "documents", label: "Documents Only", icon: FileText },
              { id: "images", label: "Images Only", icon: Image },
              { id: "audio", label: "Audio Only", icon: Music },
              { id: "video", label: "Video Only", icon: Play },
              { id: "platforms", label: "Platforms List", icon: Database },
              { id: "indexing_center", label: "Indexing Center", icon: RefreshCw }
            ].map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  id={`sidebar_tab_${item.id}`}
                  onClick={() => handleSidebarTabClick(item.id)}
                  className={`w-full flex items-center gap-3.5 px-3 py-2.5 rounded-xl text-xs font-semibold tracking-wide transition-all cursor-pointer ${isActive
                    ? "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/40"
                    }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-blue-600 dark:text-blue-400" : "text-slate-400 dark:text-slate-500"}`} />
                  {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                </button>
              );
            })}
          </nav>
        </div>

        {/* User profile footer section */}
        <div className="p-3 border-t border-slate-150 dark:border-slate-800/60">
          <button
            onClick={onLogout}
            className="w-full flex items-center gap-3 p-2 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-xl cursor-pointer text-left transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center font-bold text-blue-700 dark:text-blue-450 text-xs">
              U
            </div>
            {!sidebarCollapsed && (
              <div className="min-w-0 flex-1">
                <span className="block text-xs font-bold text-slate-700 dark:text-slate-300 truncate">
                  User Account
                </span>
                <span className="block text-[10px] text-slate-400 dark:text-slate-550 truncate">
                  pkmahajan2020@gmail.com
                </span>
              </div>
            )}
          </button>
        </div>
      </motion.aside>

      {/* 2. Right Base Content Stage with spacer to layout sidebar */}
      <div
        style={{ paddingLeft: sidebarCollapsed ? "68px" : "250px" }}
        className="min-h-screen w-full flex flex-col justify-between transition-all duration-300"
      >

        {/* 3. Top Navigation - Portal Searchable status */}
        <header id="dashboard_topnav" className="h-16 border-b border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20 transition-colors duration-200">
          <div>
            <h3 className="font-display font-bold text-sm text-slate-800 dark:text-slate-100">
              {activeTab === "dashboard" ? "Unified Search Command" : activeTab === "indexing_center" ? "Indexing Operations Office" : "Integrations Cabinet"}
            </h3>
          </div>

          <div className="flex items-center gap-4">
            {/* Clickable portal index status summary */}
            <div
              id="top_platforms_status_link"
              onClick={() => setActiveTab("indexing_center")}
              className="hidden lg:flex items-center gap-2 p-1.5 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 rounded-xl cursor-pointer hover:shadow-2xs transition-all"
              title="Click to view Indexing Center"
            >
              <div className="flex -space-x-1 pl-1 items-center">
                {platforms.filter((p) => p.connected).map((p) => {
                  const isIndexed = indexedPlatforms.includes(p.id);
                  return (
                    <div
                      key={p.id}
                      className="w-5 h-5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center"
                      title={`${p.name}: ${isIndexed ? "Searchable" : "Not indexed"}`}
                    >
                      {renderPlatformLogo(p.iconName, p.color, "w-3 h-3")}
                    </div>
                  );
                })}
              </div>

              <div className="text-right px-1.5 border-l border-slate-200 dark:border-slate-800">
                <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 block font-normal leading-tight">Portals Search Ready</span>
                <span className="text-xs font-bold text-slate-700 dark:text-slate-350 block">
                  🟢 {indexedPlatforms.length} / {platforms.filter((p) => p.connected).length} Connected
                </span>
              </div>
            </div>

            {/* Alternated Compact Status (Tablet / Mobile representation) */}
            <button
              onClick={() => setActiveTab("indexing_center")}
              className="lg:hidden flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-950/40 border border-blue-100 dark:border-blue-900/30 rounded-full text-xs font-semibold text-blue-700 dark:text-blue-400 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Ready: {indexedPlatforms.length}/{platforms.filter((p) => p.connected).length}</span>
            </button>

            {/* Elegant Theme Toggle Button */}
            <button
              type="button"
              onClick={onToggleTheme}
              className="p-2.5 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/80 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-amber-400 transition-all cursor-pointer active:scale-95 flex items-center justify-center shadow-3xs"
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {theme === "dark" ? (
                <Sun className="w-4 h-4 text-amber-500" />
              ) : (
                <Moon className="w-4 h-4 text-slate-500" />
              )}
            </button>
          </div>
        </header>

        {/* 4. Active Sub-View Body */}
        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">

          {/* =======================================================
              SUB-VIEW A: MAIN SEARCH DASHBOARD VIEW
              ======================================================= */}
          {activeTab === "dashboard" && (
            <div id="search_view_stage" className="space-y-6">

              {/* Gemini centric large spacious searching area */}
              {!query && (
                <div className="py-12 text-center max-w-xl mx-auto">
                  {/* Layered Orbit Lens Logo for CogniSeek */}
                  <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                    className="relative w-20 h-20 mx-auto mb-6 flex items-center justify-center select-none"
                  >
                    {/* Outer glowing aura */}
                    <div className="absolute inset-2 bg-blue-500/15 rounded-[22px] blur-xl animate-pulse" />

                    {/* Outer layered superellipse ring with Tailwind v4 standard style */}
                    <div className="absolute inset-0 bg-gradient-to-tr from-blue-600 to-indigo-500 rounded-[22px] shadow-lg shadow-blue-500/15 border border-white/15 p-0.5 flex items-center justify-center">

                      {/* Orbit tracker concentric ring */}
                      <div className="w-full h-full rounded-[20px] border border-white/10 flex items-center justify-center relative overflow-hidden">

                        {/* Background subtle rotating grid lines */}
                        <div className="absolute inset-0 border border-white/5 rounded-full scale-135 animate-spin opacity-40" style={{ animationDuration: '24s' }} />
                        <div className="absolute w-12 h-12 rounded-full border border-dashed border-white/10 opacity-30" />

                        {/* Central Lens hub */}
                        <div className="relative w-9 h-9 bg-white/10 backdrop-blur-md border border-white/20 shadow-inner rounded-xl flex items-center justify-center">
                          <Search className="w-4.5 h-4.5 text-white drop-shadow-sm" />

                          {/* Top right glint core */}
                          <span className="absolute top-1 right-1 w-1 h-1 bg-cyan-300 rounded-full animate-ping" />
                          <span className="absolute top-1 right-1 w-1 h-1 bg-cyan-300 rounded-full" />
                        </div>

                      </div>
                    </div>

                    {/* Left orbital moon */}
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 12, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-0 pointer-events-none"
                    >
                      <span className="absolute top-0.5 left-1/2 -translate-x-1/2 w-2 h-2 bg-indigo-300 rounded-full border border-white shadow-xs" />
                    </motion.div>
                  </motion.div>

                  <h1 className="font-display font-bold text-3xl text-slate-800 tracking-tight leading-none">
                    Search across your world
                  </h1>
                  <p className="text-xs text-slate-400 mt-2 max-w-sm mx-auto">
                    Unified enterprise seek engine. Query files, codes, catalogs, snapshots, and recordings instantly.
                  </p>
                </div>
              )}

              {/* Centered Integrated Search Bar Form block */}
              <form onSubmit={handleSearchSubmit} className="max-w-3xl mx-auto relative z-10">
                <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 shadow-lg shadow-slate-100/50 dark:shadow-slate-950/40 p-1.5 flex flex-col md:flex-row items-center gap-2 transition-colors duration-200">

                  {/* Text Input area */}
                  <div className="flex-1 flex items-center gap-2.5 px-3 w-full">
                    <Search className="w-5 h-5 text-slate-400 dark:text-slate-500 shrink-0" />
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search papers, code deployment yaml, team standup audio transcripts..."
                      className="w-full text-sm font-medium text-slate-850 dark:text-slate-100 placeholder-slate-400 bg-transparent py-2.5 focus:outline-none"
                    />
                    {query && (
                      <button
                        type="button"
                        onClick={clearSearch}
                        className="text-xs font-semibold text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 bg-slate-105 dark:bg-slate-800 px-2.5 py-1 rounded-md"
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  {/* Right hand selector elements */}
                  <div className="flex items-center gap-2 shrink-0 border-t md:border-t-0 md:border-l border-slate-100 dark:border-slate-800 pt-2 md:pt-0 pl-0 md:pl-2 w-full md:w-auto overflow-visible relative">

                    {/* Search Type selector - Rounded-Full both edges */}
                    <div className="relative shrink-0">
                      <button
                        type="button"
                        id="search_type_btn"
                        onClick={() => {
                          setSearchTypeOpen(!searchTypeOpen);
                          setPlatformOpen(false);
                        }}
                        className="flex items-center bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 rounded-full px-3.5 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-805 dark:hover:text-white cursor-pointer select-none gap-2 transition-colors duration-150"
                      >
                        <ListFilter className="w-3.5 h-3.5 text-slate-550 dark:text-slate-400 shrink-0" />
                        <span>
                          {SEARCH_TYPES.find((t) => t.id === searchType)?.label || "All Types"}
                        </span>
                        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform duration-200 ${searchTypeOpen ? 'rotate-180' : ''}`} />
                      </button>

                      <AnimatePresence>
                        {searchTypeOpen && (
                          <>
                            {/* Backdrop click away */}
                            <div
                              className="fixed inset-0 z-40 bg-transparent cursor-default"
                              onClick={() => setSearchTypeOpen(false)}
                            />
                            <motion.div
                              initial={{ opacity: 0, y: 4, scale: 0.95 }}
                              animate={{ opacity: 1, y: 0, scale: 1 }}
                              exit={{ opacity: 0, y: 4, scale: 0.95 }}
                              transition={{ duration: 0.12, ease: "easeOut" }}
                              className="absolute right-0 mt-1.5 w-44 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-xl shadow-slate-150/40 dark:shadow-slate-950/60 z-50 p-1.5 flex flex-col gap-0.5 border-t-slate-150 dark:border-t-slate-800"
                            >
                              {SEARCH_TYPES.map((t) => {
                                const isSelected = searchType === t.id;
                                return (
                                  <button
                                    key={t.id}
                                    type="button"
                                    onClick={() => {
                                      setSearchType(t.id);
                                      setSearchTypeOpen(false);
                                    }}
                                    className={`w-full text-left px-3.5 py-2 text-xs font-semibold flex items-center justify-between rounded-xl transition-colors ${isSelected
                                      ? "bg-blue-600 text-white"
                                      : "text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-850 dark:hover:text-white"
                                      }`}
                                  >
                                    <span>{t.label}</span>
                                    {isSelected && <Check className="w-3.5 h-3.5 text-current shrink-0" />}
                                  </button>
                                );
                              })}
                            </motion.div>
                          </>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* Platform source select filter - Rounded-Full both edges */}
                    <div className="relative shrink-0">
                      <button
                        type="button"
                        id="platform_filter_btn"
                        onClick={() => {
                          setPlatformOpen(!platformOpen);
                          setSearchTypeOpen(false);
                        }}
                        className="flex items-center bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 rounded-full px-3.5 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-805 dark:hover:text-white cursor-pointer select-none gap-2 transition-colors duration-150"
                      >
                        <span>
                          {platformFilter === "all" ? "All Channels" : (platforms.find((p) => p.id === platformFilter)?.name || "All Channels")}
                        </span>
                        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform duration-200 ${platformOpen ? 'rotate-180' : ''}`} />
                      </button>

                      <AnimatePresence>
                        {platformOpen && (
                          <>
                            {/* Backdrop click away */}
                            <div
                              className="fixed inset-0 z-40 bg-transparent cursor-default"
                              onClick={() => setPlatformOpen(false)}
                            />
                            <motion.div
                              initial={{ opacity: 0, y: 4, scale: 0.95 }}
                              animate={{ opacity: 1, y: 0, scale: 1 }}
                              exit={{ opacity: 0, y: 4, scale: 0.95 }}
                              transition={{ duration: 0.12, ease: "easeOut" }}
                              className="absolute right-0 mt-1.5 w-52 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-xl shadow-slate-150/40 dark:shadow-slate-950/60 z-50 p-1.5 flex flex-col gap-0.5 border-t-slate-150 dark:border-t-slate-800"
                            >
                              <button
                                type="button"
                                onClick={() => {
                                  setPlatformFilter("all");
                                  setPlatformOpen(false);
                                }}
                                className={`w-full text-left px-3.5 py-2 text-xs font-semibold flex items-center justify-between rounded-xl transition-colors ${platformFilter === "all"
                                  ? "bg-blue-600 text-white"
                                  : "text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-800 dark:hover:text-white"
                                  }`}
                              >
                                <span>All Channels</span>
                                {platformFilter === "all" && <Check className="w-3.5 h-3.5 text-current shrink-0" />}
                              </button>

                              {platforms.filter((p) => p.connected).map((p) => {
                                const isSelected = platformFilter === p.id;
                                return (
                                  <button
                                    key={p.id}
                                    type="button"
                                    onClick={() => {
                                      setPlatformFilter(p.id);
                                      setPlatformOpen(false);
                                    }}
                                    className={`w-full text-left px-3.5 py-2 text-xs font-semibold flex items-center gap-2 justify-between rounded-xl transition-colors ${isSelected
                                      ? "bg-blue-600 text-white"
                                      : "text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-805 hover:text-slate-800 dark:hover:text-white"
                                      }`}
                                  >
                                    <div className="flex items-center gap-1.5 min-w-0">
                                      {renderPlatformLogo(p.iconName, isSelected ? "text-white" : p.color, "w-3 h-3")}
                                      <span className="truncate">{p.name}</span>
                                    </div>
                                    {isSelected && <Check className="w-3.5 h-3.5 text-current shrink-0" />}
                                  </button>
                                );
                              })}
                            </motion.div>
                          </>
                        )}
                      </AnimatePresence>
                    </div>

                  </div>
                </div>
              </form>

              {/* CONDITIONAL BRANCH A: Display Suggestions Area if search Query is blank */}
              {!query ? (
                <div className="max-w-3xl mx-auto space-y-6">
                  <div className="border-b border-slate-200 dark:border-slate-800 pb-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-550">
                      System Indexing Insights
                    </h3>
                  </div>

                  {/* 6 KPI Cards Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    {/* Total Indexed Files */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-5 shadow-3xs hover:shadow-2xs transition-shadow">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-blue-50 dark:bg-blue-950/45 text-blue-600 dark:text-blue-400 rounded-xl">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="block text-[10px] font-bold text-slate-450 dark:text-slate-500 uppercase tracking-wide">Total Indexed</span>
                          <span className="block text-xl font-bold text-slate-800 dark:text-white font-mono mt-0.5">
                            {stats.indexedFiles}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Documents */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-5 shadow-3xs hover:shadow-2xs transition-shadow">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-indigo-50 dark:bg-indigo-950/45 text-indigo-600 dark:text-indigo-400 rounded-xl">
                          <FolderOpen className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="block text-[10px] font-bold text-slate-450 dark:text-slate-500 uppercase tracking-wide">Documents</span>
                          <span className="block text-xl font-bold text-slate-800 dark:text-white font-mono mt-0.5">
                            {Math.max(0, stats.indexedFiles - stats.indexedImages - stats.indexedAudio - stats.indexedVideos)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Images */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-5 shadow-3xs hover:shadow-2xs transition-shadow">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-emerald-50 dark:bg-emerald-950/45 text-emerald-600 dark:text-emerald-400 rounded-xl">
                          <Image className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="block text-[10px] font-bold text-slate-450 dark:text-slate-500 uppercase tracking-wide">Images</span>
                          <span className="block text-xl font-bold text-slate-800 dark:text-white font-mono mt-0.5">
                            {stats.indexedImages}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Audio */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-5 shadow-3xs hover:shadow-2xs transition-shadow">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-amber-50 dark:bg-amber-950/45 text-amber-600 dark:text-amber-400 rounded-xl">
                          <Music className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="block text-[10px] font-bold text-slate-455 dark:text-slate-500 uppercase tracking-wide">Audio</span>
                          <span className="block text-xl font-bold text-slate-800 dark:text-white font-mono mt-0.5">
                            {stats.indexedAudio}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Video */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-5 shadow-3xs hover:shadow-2xs transition-shadow">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-purple-50 dark:bg-purple-950/45 text-purple-600 dark:text-purple-400 rounded-xl">
                          <Video className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="block text-[10px] font-bold text-slate-450 dark:text-slate-500 uppercase tracking-wide">Video</span>
                          <span className="block text-xl font-bold text-slate-800 dark:text-white font-mono mt-0.5">
                            {stats.indexedVideos}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Connected Platforms */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-5 shadow-3xs hover:shadow-2xs transition-shadow">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-rose-50 dark:bg-rose-950/45 text-rose-600 dark:text-rose-400 rounded-xl">
                          <Link2 className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="block text-[10px] font-bold text-slate-450 dark:text-slate-500 uppercase tracking-wide">Connected</span>
                          <span className="block text-xl font-bold text-slate-800 dark:text-white font-mono mt-0.5">
                            {stats.connectedPlatforms} / 4
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Informational Hint panel below stats */}
                  <div className="p-4 bg-slate-100/40 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800 rounded-2xl text-center">
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                      💡 <strong>Unified Semantic Seeking</strong>: Start typing in the search bar above to instantly find papers, codebases, audio transcripts, or imagery references.
                    </p>
                  </div>
                </div>
              ) : (
                /* CONDITIONAL BRANCH B: Display Search Results Page */
                <div id="search_results_page_container" className="max-w-3xl mx-auto space-y-4 pt-2">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-medium px-1">
                    <span>
                      Discovered {matchingResults.length} matching result{matchingResults.length === 1 ? "" : "s"} inside indexed files
                    </span>
                    <span>
                      Filtered to: <strong className="capitalize text-slate-600">{searchType}</strong> &middot; <strong className="capitalize text-slate-600">{platformFilter}</strong>
                    </span>
                  </div>

                  {/* Matching Grid log */}
                  <div className="space-y-3">
                    {matchingResults.length > 0 ? (
                      matchingResults.map((file) => {
                        const platformObj = platforms.find((p) => p.id === file.platform);
                        return (
                          <motion.div
                            key={file.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/85 rounded-2xl p-5 hover:border-blue-300 dark:hover:border-slate-700 hover:shadow-xs transition-all relative group flex flex-col"
                          >
                            <div className="flex items-start gap-4">
                              <div className="p-3 bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-850 rounded-xl shrink-0">
                                {getFileIcon(file.type)}
                              </div>

                              <div className="min-w-0 flex-1">
                                <div className="flex items-start justify-between">
                                  <h4 className="font-display font-bold text-slate-800 dark:text-slate-200 text-sm group-hover:text-blue-600 dark:group-hover:text-blue-400 break-all pr-4">
                                    {file.name}
                                  </h4>
                                </div>

                                {/* Content Preview highlighting matches */}
                                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 leading-relaxed font-normal">
                                  {renderHighlightedSnippet(file.content, query)}
                                </p>
                              </div>
                            </div>

                            {/* Metadata segment */}
                            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 text-[10px] text-slate-400 dark:text-slate-500 font-medium">
                              {platformObj && (
                                <span className="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-850 text-slate-600 dark:text-slate-350 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                                  {renderPlatformLogo(platformObj.iconName, platformObj.color, "w-2.5 h-2.5")}
                                  {platformObj.name}
                                </span>
                              )}

                              <span>&bull;</span>
                              <span>Size: <strong className="font-mono text-slate-700 dark:text-slate-300">{file.size}</strong></span>
                              <span>&bull;</span>
                              <span>Last Modified: <strong className="font-mono text-slate-700 dark:text-slate-300">{file.modifiedDate}</strong></span>
                              <span>&bull;</span>
                              <span className="inline-flex items-center gap-1 bg-blue-50/85 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 border border-blue-100/30 dark:border-blue-900/30 px-2 py-0.5 rounded-full font-bold">
                                Relevance: {file.name.toLowerCase().includes(query.toLowerCase()) ? "98%" : "84%"}
                              </span>
                            </div>

                            {/* Actions segment */}
                            <div className="flex items-center justify-end gap-2 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/65">
                              <button
                                type="button"
                                onClick={() => setActiveModalFile(file)}
                                className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-600 dark:text-slate-350 hover:bg-slate-50 dark:hover:bg-slate-850 hover:text-slate-800 dark:hover:text-white transition-all cursor-pointer active:scale-97"
                              >
                                View Details
                              </button>
                              <button
                                type="button"
                                onClick={() => setActiveModalFile(file)}
                                className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer active:scale-97"
                              >
                                Open File
                              </button>
                            </div>
                          </motion.div>
                        );
                      })
                    ) : (
                      <div className="text-center py-16 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
                        <AlertCircle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
                        <h4 className="font-display font-medium text-slate-800 dark:text-slate-100 text-sm">
                          No indexing matches found
                        </h4>
                        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 max-w-sm mx-auto">
                          Try searching other terms like "Java Core", "yaml manifest", "Aadhaar card", "budget", or check if all platform channels are indexed.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

            </div>
          )}

          {/* =======================================================
              SUB-VIEW B: PLATFORMS VIEW
              ======================================================= */}
          {activeTab === "platforms" && (
            <div id="platforms_view_stage" className="space-y-6">
              <div className="bg-white border border-slate-200 rounded-2xl p-6">
                <h3 className="font-display font-bold text-slate-800 text-lg mb-2">
                  Unified Platforms Integration
                </h3>
                <p className="text-xs text-slate-500">
                  Manage active connections, verify synchronization, or link up cloud and local storage systems.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mt-6">
                  {platforms.map((p) => {
                    return (
                      <div
                        key={p.id}
                        className={`p-4.5 rounded-xl border flex items-center justify-between transition-all ${p.connected
                          ? "bg-slate-50/50 border-blue-200"
                          : "bg-white border-slate-200 hover:border-slate-350"
                          }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-white rounded-lg border border-slate-100">
                            {renderPlatformLogo(p.iconName, p.color, "w-6 h-6")}
                          </div>
                          <div>
                            <span className="block text-xs font-bold text-slate-800 truncate">{p.name}</span>
                            <span className="text-[10px] text-slate-400 block mt-0.5">
                              {p.connected ? "🟢 Linked & Searchable" : "⚪ Off-line"}
                            </span>
                          </div>
                        </div>

                        <button
                          onClick={() => {
                            const updated = platforms.map((item) => {
                              if (item.id === p.id) {
                                return { ...item, connected: !item.connected, status: item.connected ? ("idle" as const) : ("waiting" as const) };
                              }
                              return item;
                            });
                            onUpdatePlatforms(updated);
                          }}
                          className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer ${p.connected
                            ? "bg-rose-50 text-rose-600 hover:bg-rose-100"
                            : "bg-slate-900 text-white hover:bg-slate-805"
                            }`}
                        >
                          {p.connected ? "Revoke" : "Link"}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* =======================================================
              SUB-VIEW C: INDEXING CENTER
              ======================================================= */}
          {activeTab === "indexing_center" && (
            <PageIndexingCenter
              isOnboarding={false}
              platforms={platforms}
              onUpdatePlatforms={onUpdatePlatforms}
              indexedPlatforms={indexedPlatforms}
              onUpdateIndexedPlatforms={onUpdateIndexedPlatforms}
              stats={stats}
              onUpdateStats={onUpdateStats}
              theme={theme}
              onToggleTheme={onToggleTheme}
              streamFeed={streamFeed}
            />
          )}




        </main>

        {/* 5. Minimal footer */}
        <footer className="h-12 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-[#0f172a] px-6 flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500 tracking-wide font-normal transition-colors duration-200">
          <span>CogniSeek Enterprise Search • Build v3.2.1-Stellar</span>
          <span>pkmahajan2020@gmail.com</span>
        </footer>

      </div>

      {/* File Details / Open File Modal Overlay */}
      <AnimatePresence>
        {activeModalFile && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col"
            >
              {/* Header */}
              <div className="p-5 border-b border-slate-100 dark:border-slate-800/80 flex justify-between items-center bg-slate-50/50 dark:bg-slate-950/40">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-2 bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 rounded-lg">
                    {getFileIcon(activeModalFile.type)}
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-display font-bold text-slate-800 dark:text-slate-100 text-sm md:text-base truncate break-all pr-4">
                      {activeModalFile.name}
                    </h3>
                    <p className="text-[10px] font-mono text-slate-400 dark:text-slate-500 mt-0.5 truncate">
                      {activeModalFile.platform === "local_storage"
                        ? `C:\\Users\\Account\\${activeModalFile.folder || "Documents"}\\${activeModalFile.name}`
                        : `https://${activeModalFile.platform}.com/share/item/${activeModalFile.id}`}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveModalFile(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Content Body split in two columns on desktop */}
              <div className="p-6 grid grid-cols-1 md:grid-cols-12 gap-6 overflow-y-auto max-h-[70vh]">

                {/* Left metadata specifications panel */}
                <div className="md:col-span-5 space-y-4">
                  <div className="space-y-3">
                    <h4 className="text-[10px] font-bold font-mono uppercase tracking-wider text-slate-400 dark:text-slate-500">
                      File Specifications
                    </h4>

                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between py-1.5 border-b border-slate-50 dark:border-slate-850">
                        <span className="text-slate-400">Source Platform</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-300 capitalize">{activeModalFile.platform.replace("_", " ")}</span>
                      </div>
                      <div className="flex justify-between py-1.5 border-b border-slate-50 dark:border-slate-850">
                        <span className="text-slate-400">Content Type</span>
                        <span className="font-semibold text-slate-700 dark:text-slate-300 capitalize">{activeModalFile.type}</span>
                      </div>
                      <div className="flex justify-between py-1.5 border-b border-slate-50 dark:border-slate-850">
                        <span className="text-slate-400">File Capacity</span>
                        <span className="font-semibold font-mono text-slate-700 dark:text-slate-300">{activeModalFile.size}</span>
                      </div>
                      <div className="flex justify-between py-1.5 border-b border-slate-50 dark:border-slate-850">
                        <span className="text-slate-400">Last Indexed</span>
                        <span className="font-semibold font-mono text-slate-700 dark:text-slate-300">{activeModalFile.modifiedDate}</span>
                      </div>
                      {activeModalFile.folder && (
                        <div className="flex justify-between py-1.5 border-b border-slate-50 dark:border-slate-850">
                          <span className="text-slate-400">Local Directory</span>
                          <span className="font-semibold text-slate-700 dark:text-slate-300">{activeModalFile.folder}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-850">
                    <div className="flex items-start gap-2 text-[11px] text-slate-500 dark:text-slate-450 leading-relaxed">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-slate-700 dark:text-slate-200">Local OCR & Index verified</span>
                        <p className="mt-0.5">This file is parsed, indexed, and available for dynamic localized retrieval models.</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right content / extracted logs panel */}
                <div className="md:col-span-7 flex flex-col space-y-2">
                  <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Extracted Semantic Content
                  </span>

                  <div className="flex-1 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-xl p-4 font-mono text-[11px] text-slate-650 dark:text-slate-300 leading-relaxed overflow-y-auto max-h-56 min-h-[11rem] whitespace-pre-wrap select-text">
                    {activeModalFile.content}
                  </div>
                </div>

              </div>

              {/* Actions Footer */}
              <div className="p-4 border-t border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-950/40 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setActiveModalFile(null)}
                  className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-600 dark:text-slate-350 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-850 dark:hover:text-white transition-all cursor-pointer"
                >
                  Close Document
                </button>
                <button
                  type="button"
                  onClick={() => {
                    alert(`Simulating opening of native file: ${activeModalFile.name}`);
                  }}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
                >
                  Launch App & Open
                </button>
              </div>

            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
