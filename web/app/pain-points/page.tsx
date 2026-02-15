"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import type { PainPointListItem } from "@/lib/types";
import { useRequireAuth } from "@/lib/useRequireAuth";

const categories = [
  "all",
  "onboarding",
  "approvals",
  "reporting",
  "comms",
  "finance_ops",
  "sales_ops",
  "client_ops",
  "access_mgmt",
  "other",
];

export default function PainPointsPage() {
  const { ready } = useRequireAuth();
  const [items, setItems] = useState<PainPointListItem[]>([]);
  const [team, setTeam] = useState("all");
  const [category, setCategory] = useState("all");
  const [priorityMin, setPriorityMin] = useState("");
  const [error, setError] = useState("");

  const teams = useMemo(() => {
    return ["all", ...Array.from(new Set(items.map((item) => item.team)))];
  }, [items]);

  useEffect(() => {
    if (!ready) {
      return;
    }

    const params = new URLSearchParams();
    if (team !== "all") {
      params.set("team", team);
    }
    if (category !== "all") {
      params.set("category", category);
    }
    if (priorityMin) {
      params.set("priority_min", priorityMin);
    }

    apiFetch<PainPointListItem[]>(`/pain-points?${params.toString()}`)
      .then(setItems)
      .catch((err) => setError(err.message));
  }, [ready, team, category, priorityMin]);

  if (!ready) {
    return <div className="p-8 text-sm text-slate-700">Authorising...</div>;
  }

  return (
    <AppShell>
      <section className="card p-4">
        <div className="flex flex-wrap gap-3">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.12em] text-slate-500">Team</label>
            <select className="input min-w-40" value={team} onChange={(e) => setTeam(e.target.value)}>
              {teams.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.12em] text-slate-500">Category</label>
            <select className="input min-w-44" value={category} onChange={(e) => setCategory(e.target.value)}>
              {categories.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.12em] text-slate-500">Priority &gt;=</label>
            <input
              className="input min-w-32"
              value={priorityMin}
              type="number"
              step="0.01"
              onChange={(e) => setPriorityMin(e.target.value)}
              placeholder="Any"
            />
          </div>
        </div>
      </section>

      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}

      <section className="card mt-4 overflow-x-auto p-2">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.12em] text-slate-500">
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Team</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Impact</th>
              <th className="px-3 py-2">Effort</th>
              <th className="px-3 py-2">Confidence</th>
              <th className="px-3 py-2">Priority</th>
              <th className="px-3 py-2">Tags</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-800">
                  <Link href={`/pain-points/${item.id}`} className="underline-offset-2 hover:underline">
                    {item.title}
                  </Link>
                </td>
                <td className="px-3 py-2 text-slate-700">{item.team}</td>
                <td className="px-3 py-2 text-slate-700">{item.category}</td>
                <td className="px-3 py-2 text-slate-700">{item.impact_hours_per_week ?? "-"}</td>
                <td className="px-3 py-2 text-slate-700">{item.effort_score ?? "-"}</td>
                <td className="px-3 py-2 text-slate-700">{item.confidence_score ?? "-"}</td>
                <td className="px-3 py-2 text-slate-700">{item.priority_score ?? "-"}</td>
                <td className="px-3 py-2 text-xs text-slate-700">
                  {item.quick_win ? <span className="rounded bg-teal-100 px-2 py-1 text-teal-800">quick win</span> : null}
                  {item.sensitive_flag ? <span className="ml-1 rounded bg-amber-100 px-2 py-1 text-amber-800">sensitive</span> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </AppShell>
  );
}
