"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { DashboardMetrics } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function DashboardPage() {
  const { ready } = useRequireAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) {
      return;
    }

    apiFetch<DashboardMetrics>("/dashboard")
      .then(setMetrics)
      .catch((err) => setError(err.message));
  }, [ready]);

  const topTeams = useMemo(() => metrics?.team_heatmap.slice(0, 4) || [], [metrics]);

  if (!ready) {
    return <div className="p-8 text-sm text-slate-700">Authorising...</div>;
  }

  return (
    <AppShell>
      <section className="mb-4 rounded-2xl bg-gradient-to-br from-slate-900 to-cyan-900 p-6 text-white">
        <p className="text-xs uppercase tracking-[0.16em] text-cyan-200">Operations Intelligence</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight">COO Friction Dashboard</h2>
        <p className="mt-2 max-w-3xl text-sm text-cyan-100">
          Prioritise automation with transparent impact/effort/confidence scoring across teams.
        </p>
      </section>

      {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Pain Points" value={metrics?.total_pain_points ?? 0} />
        <Kpi label="Hours Lost / Week" value={metrics?.total_hours_per_week ?? 0} />
        <Kpi label="Quick Wins" value={metrics?.quick_wins.length ?? 0} />
        <Kpi label="Top Backlog Items" value={metrics?.top_backlog.length ?? 0} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <section className="card p-4">
          <h3 className="text-sm font-semibold uppercase tracking-[0.13em] text-slate-500">Top Categories</h3>
          <div className="mt-3 space-y-2">
            {metrics?.top_categories.map((item) => (
              <div key={item.category} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                <span className="text-sm capitalize text-slate-700">{item.category.replace("_", " ")}</span>
                <span className="text-sm font-semibold text-slate-900">{item.count}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="card p-4">
          <h3 className="text-sm font-semibold uppercase tracking-[0.13em] text-slate-500">Top Teams</h3>
          <div className="mt-3 space-y-3">
            {topTeams.map((item) => (
              <div key={item.team}>
                <div className="mb-1 flex items-center justify-between text-sm text-slate-700">
                  <span>{item.team}</span>
                  <span className="font-semibold">{item.total}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-teal-600 to-cyan-500"
                    style={{ width: `${Math.min(100, item.total * 6)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="card mt-4 p-4">
        <h3 className="text-sm font-semibold uppercase tracking-[0.13em] text-slate-500">Top Backlog</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.12em] text-slate-500">
                <th className="px-2 py-2">Pain Point</th>
                <th className="px-2 py-2">Team</th>
                <th className="px-2 py-2">Impact</th>
                <th className="px-2 py-2">Priority</th>
                <th className="px-2 py-2">Approach</th>
              </tr>
            </thead>
            <tbody>
              {metrics?.top_backlog.map((item) => (
                <tr key={item.pain_point_id} className="border-b border-slate-100">
                  <td className="px-2 py-2 font-medium text-slate-800">{item.title}</td>
                  <td className="px-2 py-2 text-slate-700">{item.team}</td>
                  <td className="px-2 py-2 text-slate-700">{item.impact_hours_per_week}</td>
                  <td className="px-2 py-2 text-slate-700">{item.priority_score}</td>
                  <td className="px-2 py-2 text-slate-700">{item.automation_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}

function Kpi({ label, value }: { label: string; value: number }) {
  return (
    <article className="card p-4">
      <p className="text-xs uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-ink">{value}</p>
    </article>
  );
}
