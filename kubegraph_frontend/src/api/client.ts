// Fetch wrapper: attaches the Bearer token, throws ApiError on failure, and
// broadcasts a 'kg-unauthorized' event on 401 so the auth layer can log out.

import type {
  BlastRadius, FleetItem, GraphResponse, PathResponse, Remediation, Stats, TokenResponse, User,
} from "./types";

const BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";
const TOKEN_KEY = "kg_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${BASE}`);
  }

  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent("kg-unauthorized"));
    throw new ApiError(401, "Session expired — please sign in again");
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,

  // auth
  register: (b: { name: string; email: string; password: string; org?: string; role?: string }) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify(b) }),
  login: (b: { email: string; password: string }) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(b) }),
  me: () => request<User>("/auth/me"),

  // cluster / analysis
  loadDemo: () => request<{ snapshot_id: string; stats: Stats }>("/demo", { method: "POST" }),
  snapshots: () => request<{ snapshot_id: string; cluster_name: string; current: boolean }[]>("/snapshots"),
  stats: () => request<Stats>("/stats"),
  fleet: () => request<FleetItem[]>("/fleet"),
  graph: () => request<GraphResponse>("/graph"),
  paths: () => request<PathResponse[]>("/paths"),
  remediations: (top = 12) => request<Remediation[]>(`/remediations?top=${top}`),
  blastRadius: (node: string) => request<BlastRadius>(`/blast-radius?node=${encodeURIComponent(node)}`),
};
