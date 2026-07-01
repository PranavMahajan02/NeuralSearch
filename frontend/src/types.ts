/**
 * CogniSeek TypeScript Types
 */

export type PlatformId =
  | "google_drive"
  | "google_photos"
  | "github"
  | "local_storage";

export interface Platform {
  id: PlatformId;
  name: string;
  connected: boolean;
  indexed: boolean;
  status: "idle" | "waiting" | "indexing" | "indexed" | "paused";
  progress: number; // 0 to 100
  iconName: string;
  color: string;
  selectedFolders?: string[]; // Only for local_storage
  customFolderName?: string;  // Only for Custom Folder
}

export type FileType = "document" | "image" | "audio" | "video";

export interface MockFile {
  id: string;
  name: string;
  type: FileType;
  platform: PlatformId;
  size: string;
  modifiedDate: string;
  preview: string;
  content: string; // Background text content for search matching
  isFavorite?: boolean;
  searchCount?: number;
  folder?: string; // Optional folder path/category (for local storage specific folders)
}

export interface IndexLog {
  id: string;
  fileName: string;
  platform: PlatformId;
  status: "processing" | "success" | "warning";
  timestamp: string;
  type: FileType;
}

export type SearchType = "all" | "document" | "image" | "audio" | "video";

export interface DashboardStats {
  connectedPlatforms: number;
  indexedFiles: number;
  indexedImages: number;
  indexedAudio: number;
  indexedVideos: number;
  platformsReady: number;
  lastSyncTime: string;
  totalSearches: number;
  storageUsageGbs: number;
}

export interface AuthUser {
  id: number;
  name: string;
  email: string;
}
