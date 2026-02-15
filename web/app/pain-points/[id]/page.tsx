"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { apiGet } from "@/lib/api";
import type { PainPointDetail } from "@/lib/types";

export default function PainPointByIdPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params?.id;

  const [item, setItem] = useState<PainPointDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      return;
    }

    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiGet<PainPointDetail>(`/pain-points/${id}`);
        setItem(data);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to load pain point");
        }
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [id]);

  if (loading) {
    return <div style={{ padding: 24 }}>Loading...</div>;
  }

  if (error) {
    return <div style={{ padding: 24, color: "red" }}>{error}</div>;
  }

  if (!item) {
    return <div style={{ padding: 24 }}>Not found.</div>;
  }

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <button type="button" onClick={() => router.back()}>
          {"<- Back"}
        </button>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>{item.title}</h1>
      </div>

      <p style={{ marginTop: 12, opacity: 0.9 }}>{item.description}</p>

      <div style={{ marginTop: 16, display: "grid", gap: 8 }}>
        <div>
          <strong>Category:</strong> {item.category}
        </div>
        <div>
          <strong>Frequency / week:</strong> {item.frequency_per_week}
        </div>
        <div>
          <strong>Minutes / occurrence:</strong> {item.minutes_per_occurrence}
        </div>
        <div>
          <strong>People affected:</strong> {item.people_affected}
        </div>
        <div>
          <strong>Sensitive:</strong> {item.sensitive_flag ? "Yes" : "No"}
        </div>
      </div>

      <p style={{ marginTop: 16, fontSize: 13, opacity: 0.8 }}>
        Editing disabled in demo build.
      </p>
    </div>
  );
}
