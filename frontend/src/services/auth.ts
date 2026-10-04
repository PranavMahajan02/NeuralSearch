import { apiJson, clearToken, getToken, setToken } from "./http";

export { getToken };

export async function login(email: string, password: string) {
  const data = await apiJson<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    json: { email, password },
    auth: false,
    errorMessage: "Login failed.",
  });

  setToken(data.access_token);

  return data;
}

export async function register(name: string, email: string, password: string) {
  return apiJson("/auth/register", {
    method: "POST",
    json: { name, email, password },
    auth: false,
    errorMessage: "Registration failed.",
  });
}

export async function getProfile() {
  return apiJson("/auth/profile", { errorMessage: "Unable to fetch profile." });
}

export async function logout() {
  if (getToken()) {
    try {
      // Revokes every token of this user on the server.
      await apiJson("/auth/logout", { method: "POST" });
    } catch (e) {
      console.error(e);
    }
  }

  clearToken();
}

export function isLoggedIn() {
  return getToken() !== null;
}
