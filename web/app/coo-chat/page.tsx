"use client";

import { FormEvent, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiPost } from "@/lib/api";
import type { COOChatContext, COOChatResponse, ChatMessage } from "@/lib/types";

const starterMessage: ChatMessage = {
  role: "assistant",
  content:
    "I can help you investigate an operational complaint as the COO. Describe the issue, where it happens, and who is affected.",
};

export default function COOChatPage() {
  const [context, setContext] = useState<COOChatContext>({
    name: "",
    email: "",
    team: "COO Office",
    role: "COO",
    location: "",
    consent: false,
  });
  const [messages, setMessages] = useState<ChatMessage[]>([starterMessage]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<COOChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const payloadMessages = useMemo(
    () => messages.filter((m) => m.role === "user" || (m.role === "assistant" && m !== starterMessage)),
    [messages],
  );

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || loading) {
      return;
    }

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(nextMessages);
    setDraft("");
    setLoading(true);
    setError(null);

    try {
      const response = await apiPost<COOChatResponse>("/chatbot/coo", {
        messages: nextMessages.filter((m) => m.role !== "assistant" || m !== starterMessage),
        context,
        add_to_report: false,
      });

      setResult(response);
      setMessages((prev) => [...prev, { role: "assistant", content: response.assistant_message }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  }

  async function analyzeAndAdd() {
    if (loading) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await apiPost<COOChatResponse>("/chatbot/coo", {
        messages: payloadMessages,
        context,
        add_to_report: true,
      });

      setResult(response);
      setMessages((prev) => [...prev, { role: "assistant", content: response.assistant_message }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze concern");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <section className="mb-4 rounded-2xl bg-gradient-to-br from-emerald-900 to-teal-800 p-6 text-white">
        <p className="text-xs uppercase tracking-[0.16em] text-emerald-200">COO Assistant</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight">Complaint Root-Cause Chatbot</h2>
        <p className="mt-2 max-w-3xl text-sm text-emerald-100">
          The assistant asks probing questions, checks concern validity, and can add validated issues straight into the automation report backlog.
        </p>
      </section>

      <section className="card p-4">
        <h3 className="text-sm font-semibold uppercase tracking-[0.13em] text-slate-500">Context</h3>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <input
            className="input"
            placeholder="Name (optional)"
            value={context.name || ""}
            onChange={(e) => setContext({ ...context, name: e.target.value })}
          />
          <input
            className="input"
            placeholder="Email (optional)"
            value={context.email || ""}
            onChange={(e) => setContext({ ...context, email: e.target.value })}
          />
          <input className="input" value={context.team} onChange={(e) => setContext({ ...context, team: e.target.value })} />
          <input className="input" value={context.role} onChange={(e) => setContext({ ...context, role: e.target.value })} />
          <input
            className="input md:col-span-2"
            placeholder="Location (optional)"
            value={context.location || ""}
            onChange={(e) => setContext({ ...context, location: e.target.value })}
          />
        </div>
        <label className="mt-3 inline-flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={context.consent}
            onChange={(e) => setContext({ ...context, consent: e.target.checked })}
          />
          Consent to store transcript text
        </label>
      </section>

      <section className="card mt-4 p-4">
        <h3 className="text-sm font-semibold uppercase tracking-[0.13em] text-slate-500">Conversation</h3>
        <div className="mt-3 max-h-[420px] space-y-3 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3">
          {messages.map((msg, idx) => (
            <div
              key={`${msg.role}-${idx}`}
              className={`rounded-lg px-3 py-2 text-sm ${
                msg.role === "user" ? "ml-auto max-w-[80%] bg-teal-700 text-white" : "max-w-[85%] bg-white text-slate-800"
              }`}
            >
              {msg.content}
            </div>
          ))}
        </div>

        <form onSubmit={sendMessage} className="mt-3 flex gap-2">
          <input
            className="input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Describe the complaint, impact, and context"
          />
          <button type="submit" className="btn-primary min-w-24" disabled={loading || !draft.trim()}>
            Send
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className="btn-secondary" disabled={loading || payloadMessages.length === 0} onClick={analyzeAndAdd}>
            Analyse + Add to Report
          </button>
          {loading ? <p className="text-sm text-slate-500">Thinking...</p> : null}
        </div>

        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      </section>

      {result ? (
        <section className="card mt-4 p-4">
          <h3 className="text-sm font-semibold uppercase tracking-[0.13em] text-slate-500">Assessment</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <Metric label="Valid Concern" value={result.valid_concern ? "Yes" : "No"} />
            <Metric label="Needs More Info" value={result.needs_more_info ? "Yes" : "No"} />
            <Metric label="Category" value={result.category} />
            <Metric label="Estimated Impact (h/week)" value={result.estimated_impact_hours_per_week.toString()} />
          </div>
          <p className="mt-3 text-sm text-slate-700"><strong>Root Cause:</strong> {result.root_cause || "Not enough signal yet"}</p>
          <p className="mt-2 text-sm text-slate-600">{result.rationale}</p>

          {result.added_to_report ? (
            <p className="mt-3 rounded-lg bg-emerald-100 px-3 py-2 text-sm text-emerald-800">
              Added to report backlog. Pain point IDs: {result.pain_point_ids.join(", ")}
            </p>
          ) : null}
        </section>
      ) : null}
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-800">{value}</p>
    </div>
  );
}
