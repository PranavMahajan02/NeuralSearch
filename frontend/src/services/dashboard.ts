import { apiJson } from "./http";

export async function getDashboardStats() {
  return apiJson("/dashboard/stats", { errorMessage: "Unable to load dashboard statistics." });
}

export async function getDashboardPlatforms() {
  return apiJson("/dashboard/platforms", { errorMessage: "Unable to load dashboard platforms." });
}
