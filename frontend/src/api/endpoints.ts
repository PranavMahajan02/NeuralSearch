// One typed function per backend endpoint used by the UI.
import { apiBlob, apiJson } from "./client";
import type {
  ConnectResponse,
  DashboardStats,
  DisconnectResponse,
  DriveStatus,
  FoldersResponse,
  GithubStatus,
  IndexQueuedResponse,
  JobErrorsResponse,
  Job,
  JobWithHistory,
  LoginStateResponse,
  OpenResponse,
  PickFolderResponse,
  PlatformName,
  RecentResponse,
  RegisterRequest,
  SearchRequest,
  SearchResponse,
  SearchResult,
  SuggestionsResponse,
  TokenResponse,
  User,
} from "./types";

// ---- auth ----------------------------------------------------------------------

export const login = (email: string, password: string) =>
  apiJson<TokenResponse>("/auth/login", { method: "POST", json: { email, password }, auth: false });

export const register = (body: RegisterRequest) =>
  apiJson<User>("/auth/register", { method: "POST", json: body, auth: false });

export const getProfile = (signal?: AbortSignal) => apiJson<User>("/auth/profile", { signal });

export const logout = () => apiJson<unknown>("/auth/logout", { method: "POST" });

export const changePassword = (currentPassword: string, newPassword: string) =>
  apiJson<{ status: string; message: string }>("/auth/change-password", {
    method: "POST",
    json: { current_password: currentPassword, new_password: newPassword },
  });

export const exportMyData = () => apiBlob("/auth/export");

export const deleteAccount = (password: string) =>
  apiJson<{ status: string; deleted_files: number }>("/auth/account", {
    method: "DELETE",
    json: { password },
  });

export const getLoginState = () => apiJson<LoginStateResponse>("/auth/login-state");

export const completeOnboarding = () =>
  apiJson<{ onboarding_completed: boolean }>("/auth/onboarding/complete", { method: "POST" });

export const skipOnboarding = () =>
  apiJson<{ onboarding_completed: boolean }>("/auth/onboarding/skip", { method: "POST" });

// ---- search ----------------------------------------------------------------------

export const searchFiles = (body: SearchRequest, signal?: AbortSignal) =>
  apiJson<SearchResponse>("/search/", { method: "POST", json: body, signal });

export const getSuggestions = (prefix: string, signal?: AbortSignal) =>
  apiJson<SuggestionsResponse>("/search/suggestions", { query: { prefix }, signal });

export const openTarget = (result: Pick<SearchResult, "platform" | "source_id">) =>
  apiJson<OpenResponse>("/open/", {
    method: "POST",
    json: { platform: result.platform, source_id: result.source_id },
  });

export const downloadFile = (url: string) => apiBlob(url);

export const getBackendHealth = (signal?: AbortSignal) =>
  apiJson<{ status: string }>("/search/health", { auth: false, signal });

// ---- dashboard -------------------------------------------------------------------

export const getStats = (signal?: AbortSignal) => apiJson<DashboardStats>("/dashboard/stats", { signal });

export const getRecentFiles = (signal?: AbortSignal) =>
  apiJson<RecentResponse>("/dashboard/recent", { signal });

// ---- indexing --------------------------------------------------------------------

export const JOB_HISTORY = 5;

export const getJobs = (signal?: AbortSignal) =>
  apiJson<JobWithHistory[]>("/index/jobs", { query: { history: JOB_HISTORY }, signal });

export const startIndexing = (priority: PlatformName, platforms: PlatformName[]) =>
  apiJson<IndexQueuedResponse>("/index/", {
    method: "POST",
    json: { priority_platform: priority, platforms },
  });

export const prioritizeJob = (jobId: string) =>
  apiJson<Job>(`/index/jobs/${encodeURIComponent(jobId)}/prioritize`, { method: "POST" });

export const cancelJob = (jobId: string) =>
  apiJson<Job>(`/index/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });

export const getJobErrors = (jobId: string, signal?: AbortSignal) =>
  apiJson<JobErrorsResponse>(`/index/jobs/${encodeURIComponent(jobId)}/errors`, { signal });

// ---- platforms -------------------------------------------------------------------

export type CloudPlatform = Exclude<PlatformName, "local">;

const CLOUD_PATH: Record<CloudPlatform, string> = {
  google_drive: "/platforms/google-drive",
  github: "/platforms/github",
};

export const getDriveStatus = (signal?: AbortSignal) =>
  apiJson<DriveStatus>(`${CLOUD_PATH.google_drive}/status`, { signal });

export const getGithubStatus = (signal?: AbortSignal) =>
  apiJson<GithubStatus>(`${CLOUD_PATH.github}/status`, { signal });

export const connectPlatform = (platform: CloudPlatform) =>
  apiJson<ConnectResponse>(`${CLOUD_PATH[platform]}/connect`);

export const disconnectPlatform = (platform: CloudPlatform, purge: boolean) =>
  apiJson<DisconnectResponse>(`${CLOUD_PATH[platform]}/disconnect`, { method: "POST", query: { purge } });

export const getFolders = (signal?: AbortSignal) =>
  apiJson<FoldersResponse>("/platforms/local/folders", { signal });

export const addFolder = (folder: string) =>
  apiJson<FoldersResponse>("/platforms/local/folders", { method: "POST", json: { folder } });

export const removeFolder = (folder: string) =>
  apiJson<FoldersResponse>("/platforms/local/folders", { method: "DELETE", json: { folder } });

export const pickFolder = () =>
  apiJson<PickFolderResponse>("/platforms/local/pick-folder", { method: "POST" });
