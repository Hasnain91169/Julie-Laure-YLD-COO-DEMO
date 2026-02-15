"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch, setAppPassword } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      setAppPassword(password);
      await apiFetch("/dashboard", { method: "GET" });
      router.replace("/dashboard");
    } catch {
      setError("Invalid password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-card">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Friction Finder</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">Admin Login</h1>
        <p className="mt-2 text-sm text-slate-600">
          Use your `APP_PASSWORD` from backend env to access the operations dashboard.
        </p>

        <form className="mt-6 space-y-3" onSubmit={onSubmit}>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error ? <p className="text-sm text-red-700">{error}</p> : null}

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
