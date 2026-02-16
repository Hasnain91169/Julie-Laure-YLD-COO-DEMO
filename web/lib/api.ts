const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const PW_KEY = "ff_app_password";
let appPassword: string | null = null;

export function setAppPassword(pw: string) {
  appPassword = pw;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(PW_KEY, pw);
  }
}

export function apiBase(): string {
  return API_BASE;
}

export function clearPassword(): void {
  appPassword = null;
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(PW_KEY);
  }
}

export function readPassword(): string {
  if (appPassword) return appPassword;
  if (typeof window === "undefined") return "";
  const stored = window.localStorage.getItem(PW_KEY) || "";
  if (stored) appPassword = stored;
  return stored;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}, passwordOverride?: string): Promise<T> {
  const headers = new Headers(init.headers || {});
  const pw = passwordOverride ?? readPassword();
  headers.set("Content-Type", "application/json");
  if (pw) {
    headers.set("x-app-password", pw);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
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

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function pollUntil<T>(
  fetcher: () => Promise<T>,
  condition: (result: T) => boolean,
  intervalMs = 2000,
  maxAttempts = 30
): Promise<T> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const result = await fetcher();
      if (condition(result)) {
        return result;
      }
    } catch (error) {
      // Continue polling even on error (e.g., 404 when report doesn't exist yet)
      if (i === maxAttempts - 1) {
        throw error;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("Polling timeout - max attempts reached");
}
