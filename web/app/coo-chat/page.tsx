"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiPost } from "@/lib/api";
import type { COOChatContext, COOChatResponse, ChatMessage } from "@/lib/types";

const starterMessage: ChatMessage = {
  role: "assistant",
  content: "Share what is not working operationally, and I will help unpack the root cause step by step.",
};

const STORAGE_KEY = "ff_coo_chat_state";

type StoredChatState = {
  messages: ChatMessage[];
  result: COOChatResponse | null;
};

export default function COOChatPage() {
  const [context] = useState<COOChatContext>({
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
  const conversationRef = useRef<HTMLDivElement | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const payloadMessages = useMemo(
    () => messages.filter((m) => m.role === "user" || (m.role === "assistant" && m !== starterMessage)),
    [messages],
  );

  useEffect(() => {
    if (!conversationRef.current) {
      return;
    }
    conversationRef.current.scrollTop = conversationRef.current.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    if (hydrated || typeof window === "undefined") {
      return;
    }

    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setHydrated(true);
        return;
      }
      const parsed = JSON.parse(raw) as StoredChatState;
      if (Array.isArray(parsed.messages) && parsed.messages.length > 0) {
        setMessages(parsed.messages);
      }
      if (parsed.result) {
        setResult(parsed.result);
      }
    } catch {
      // Ignore corrupted local state.
    } finally {
      setHydrated(true);
    }
  }, [hydrated]);

  useEffect(() => {
    if (!hydrated || typeof window === "undefined") {
      return;
    }

    const payload: StoredChatState = { messages, result };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }, [messages, result, hydrated]);

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
      const analysisResponse = await apiPost<COOChatResponse>("/chatbot/coo", {
        messages: nextMessages.filter((m) => m.role !== "assistant" || m !== starterMessage),
        context,
        add_to_report: false,
      });

      let finalResponse = analysisResponse;
      if (analysisResponse.valid_concern && !analysisResponse.needs_more_info) {
        finalResponse = await apiPost<COOChatResponse>("/chatbot/coo", {
          messages: nextMessages.filter((m) => m.role !== "assistant" || m !== starterMessage),
          context,
          add_to_report: true,
        });
      }

      setResult(finalResponse);
      setMessages((prev) => [...prev, { role: "assistant", content: finalResponse.assistant_message }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  }

  async function analyzeAndAdd() {
    if (loading || payloadMessages.length === 0) {
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
          Analysis runs quietly in the background while you chat. When a concern is validated, you can add it to the report backlog.
        </p>
      </section>

      <section className="card p-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-[0.13em] text-slate-500">Conversation</h3>
          <div className="text-xs text-slate-500">
            {loading ? "Analyzing..." : result ? `Last update: ${new Date(result.created_at).toLocaleTimeString()}` : "Live analysis"}
          </div>
        </div>

        <div
          ref={conversationRef}
          className="mt-3 max-h-[420px] space-y-3 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3"
        >
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
            placeholder="Tell me what is happening"
          />
          <button type="submit" className="btn-primary min-w-24" disabled={loading || !draft.trim()}>
            Send
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-secondary"
            disabled={loading || payloadMessages.length === 0}
            onClick={analyzeAndAdd}
          >
            Re-run Analysis + Add
          </button>
          {result ? (
            <p className="text-sm text-slate-600">
              {result.valid_concern && !result.needs_more_info ? "Valid concern detected." : "Listening and building signal."}
            </p>
          ) : null}
        </div>

        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        {result?.root_cause ? (
          <p className="mt-3 text-sm text-slate-700">
            <strong>Current root-cause signal:</strong> {result.root_cause}
          </p>
        ) : null}
        {result?.added_to_report ? (
          <p className="mt-3 rounded-lg bg-emerald-100 px-3 py-2 text-sm text-emerald-800">
            Added to report backlog. Pain point IDs: {result.pain_point_ids.join(", ")}
          </p>
        ) : null}
      </section>
    </AppShell>
  );
}
