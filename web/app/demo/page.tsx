"use client";

import { useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function DemoPage() {
  const { ready } = useRequireAuth();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState("");

  async function seed(reset: boolean) {
    setLoading(true);
    setError("");
    setResult("");

    try {
      const data = await apiFetch<{ respondents: number; interviews: number; pain_points: number }>(
        `/demo/seed?interview_count=24&reset=${reset}`,
        { method: "POST" },
      );
      setResult(
        `Seeded ${data.respondents} respondents, ${data.interviews} interviews, ${data.pain_points} pain points.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to seed demo data");
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return <div className="p-8 text-sm text-slate-700">Authorising...</div>;
  }

  return (
    <AppShell>
      <section className="card p-6">
        <p className="text-xs uppercase tracking-[0.15em] text-slate-500">Demo Mode</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-ink">Seed Realistic Interview Data</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          Populate the platform with 24 realistic mock interviews and 30+ pain points across People, Finance,
          Engineering, Client Services and Commercial.
        </p>

        <div className="mt-5 flex flex-wrap gap-3">
          <button type="button" className="btn-primary" disabled={loading} onClick={() => seed(false)}>
            {loading ? "Seeding..." : "Seed Additional Data"}
          </button>
          <button type="button" className="btn-secondary" disabled={loading} onClick={() => seed(true)}>
            Reset + Seed Fresh Demo
          </button>
        </div>

        {result ? <p className="mt-4 text-sm font-medium text-teal-700">{result}</p> : null}
        {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
      </section>
    </AppShell>
  );
}
