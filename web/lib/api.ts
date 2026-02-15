const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let appPassword: string | null = null;

export function setAppPassword(pw: string) {
  appPassword = pw;
}

export function apiBase(): string {
  return API_BASE;
}

export function readPassword(): string {
  if (appPassword) {
    return appPassword;
  }
  if (typeof window === "undefined") {
    return "";
  }
  const stored = window.localStorage.getItem("ff_app_password") || "";
  if (stored) {
    appPassword = stored;
  }
  return stored;
}

export function storePassword(password: string): void {
  appPassword = password;
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem("ff_app_password", password);
}

export function clearPassword(): void {
  appPassword = null;
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem("ff_app_password");
}

export async function apiFetch<T>(path: string, options: RequestInit = {}, password?: string): Promise<T> {
  const activePassword = password ?? readPassword();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (activePassword) {
    headers.set("x-app-password", activePassword);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (response.status === 401) {
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

export async function fetchHtml(path: string): Promise<string> {
  const headers = new Headers();
  const password = readPassword();
  if (password) {
    headers.set("x-app-password", password);
  }

  const response = await fetch(`${API_BASE}${path}`, { headers, cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load HTML (${response.status})`);
  }
  return await response.text();
}

export async function downloadPdf(path: string): Promise<Blob> {
  const headers = new Headers();
  const password = readPassword();
  if (password) {
    headers.set("x-app-password", password);
  }

  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    throw new Error(`Failed to export PDF (${response.status})`);
  }
  return await response.blob();
}
// Compatibility helpers used by detail pages.
export async function apiGet<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "GET" });
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}
