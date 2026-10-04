import { apiJson } from "./http";

export async function getLoginState() {
  return apiJson<{ has_indexed: boolean; platforms: string[] }>("/auth/login-state", {
    errorMessage: "Unable to load login state.",
  });
}
