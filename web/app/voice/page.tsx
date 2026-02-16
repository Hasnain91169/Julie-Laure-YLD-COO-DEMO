"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { apiGet, apiPost, pollUntil } from "@/lib/api";
import type { ReportRunResponse, SessionRequest, SessionResponse } from "@/lib/types";

export default function VoicePage() {
  const router = useRouter();
  const [formData, setFormData] = useState<SessionRequest>({
    name: "",
    email: "",
    team: "Unknown",
    role: "Unknown",
    location: "",
    consent: false,
  });

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [respondentId, setRespondentId] = useState<number | null>(null);
  const [callInProgress, setCallInProgress] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [report, setReport] = useState<ReportRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleStartSession = async () => {
    setError(null);
    try {
      // Create session
      const response = await apiPost<SessionResponse>("/intake/session", formData);
      setSessionId(response.session_id);
      setRespondentId(response.respondent_id);

      // TODO: Initialize VAPI Web SDK here when you have credentials
      // For now, simulate call flow
      alert(
        `Session created!\n\nSession ID: ${response.session_id}\nRespondent ID: ${response.respondent_id}\n\n` +
          `To enable voice calls:\n` +
          `1. Install @vapi-ai/web: npm install @vapi-ai/web\n` +
          `2. Add NEXT_PUBLIC_VAPI_PUBLIC_KEY to .env.local\n` +
          `3. Add NEXT_PUBLIC_VAPI_ASSISTANT_ID to .env.local\n` +
          `4. Uncomment VAPI integration code in this file\n\n` +
          `For now, you can test the flow by manually calling:\n` +
          `POST /intake/vapi with session_id in metadata_json`
      );

      setCallInProgress(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    }
  };

  const handleSimulateCall = () => {
    setCallInProgress(false);
    setProcessing(true);

    // Poll for report
    pollUntil<ReportRunResponse>(
      () => apiGet<ReportRunResponse>(`/report/latest?session_id=${sessionId}`),
      (result) => !!result,
      3000,
      20
    )
      .then((reportData) => {
        setReport(reportData);
        setProcessing(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Timeout waiting for report");
        setProcessing(false);
      });
  };

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Voice Intake</h1>
        <p className="mt-1 text-sm text-slate-600">
          Report friction points through voice conversation powered by VAPI.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>
      )}

      {!sessionId && (
        <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
          <h2 className="font-semibold">Your Information</h2>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700">Name (optional)</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Your name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">Email (optional)</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="you@example.com"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Team</label>
                <select
                  value={formData.team}
                  onChange={(e) => setFormData({ ...formData, team: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="Unknown">Unknown</option>
                  <option value="Engineering">Engineering</option>
                  <option value="Finance">Finance</option>
                  <option value="People">People</option>
                  <option value="Client Services">Client Services</option>
                  <option value="Commercial">Commercial</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Role</label>
                <input
                  type="text"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="Your role"
                />
              </div>
            </div>

            <div>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.consent || false}
                  onChange={(e) => setFormData({ ...formData, consent: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-slate-700">
                  I consent to storing my call transcript for analysis
                </span>
              </label>
            </div>
          </div>

          <button
            onClick={handleStartSession}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 font-medium text-white hover:bg-blue-700"
          >
            Start Voice Call
          </button>
        </div>
      )}

      {sessionId && !processing && !report && (
        <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold">Call Status</h2>
              <p className="text-sm text-slate-600">
                Session ID: <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">{sessionId}</code>
              </p>
            </div>
            <div className="flex h-3 w-3 items-center justify-center">
              <span className={`h-3 w-3 rounded-full ${callInProgress ? "bg-green-500 animate-pulse" : "bg-gray-400"}`}></span>
            </div>
          </div>

          {callInProgress && (
            <div className="rounded-lg bg-blue-50 p-4">
              <p className="text-sm text-blue-800">
                🎙️ VAPI integration placeholder - In production, the VAPI Web SDK would open here.
              </p>
              <button
                onClick={handleSimulateCall}
                className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Simulate Call Completion
              </button>
            </div>
          )}

          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-xs font-medium text-amber-900">VAPI Setup Required</p>
            <p className="mt-1 text-xs text-amber-800">
              To enable actual voice calls, add your VAPI credentials to <code>.env.local</code> and uncomment the
              VAPI integration code in this file.
            </p>
          </div>
        </div>
      )}

      {processing && (
        <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center space-x-3">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600"></div>
            <div>
              <h2 className="font-semibold">Processing Your Feedback</h2>
              <p className="text-sm text-slate-600">Waiting for n8n to generate your report...</p>
            </div>
          </div>

          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs text-slate-600">
              The n8n workflow is analyzing your pain points, generating recommendations, and creating a PDF report.
              This usually takes 30-60 seconds.
            </p>
          </div>
        </div>
      )}

      {report && (
        <div className="space-y-4 rounded-lg border border-green-200 bg-green-50 p-6">
          <div className="flex items-center space-x-3">
            <svg
              className="h-6 w-6 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <div>
              <h2 className="font-semibold text-green-900">Report Ready!</h2>
              <p className="text-sm text-green-700">Your feedback has been processed.</p>
            </div>
          </div>

          {report.summary && (
            <div className="rounded-lg bg-white p-4">
              <h3 className="text-sm font-medium text-slate-900">Summary</h3>
              <p className="mt-1 text-sm text-slate-700">{report.summary}</p>
            </div>
          )}

          <div className="flex space-x-3">
            <button
              onClick={() => router.push("/report")}
              className="flex-1 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
            >
              View Full Report
            </button>
            {report.pdf_path_or_url && (
              <a
                href={report.pdf_path_or_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2 text-center font-medium text-slate-700 hover:bg-slate-50"
              >
                Download PDF
              </a>
            )}
          </div>
        </div>
      )}

      {/* VAPI Integration Code (Commented out - uncomment when you have credentials) */}
      {/*
      <script>
        // import Vapi from '@vapi-ai/web';
        // const vapi = new Vapi(process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY);

        // In handleStartSession after getting session_id:
        // vapi.start({
        //   assistantId: process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID,
        //   metadata: {
        //     session_id: response.session_id,
        //     respondent_id: response.respondent_id
        //   }
        // });

        // vapi.on('call-start', () => {
        //   setCallInProgress(true);
        // });

        // vapi.on('call-end', () => {
        //   setCallInProgress(false);
        //   setProcessing(true);
        //   // Start polling for report
        // });

        // vapi.on('error', (error) => {
        //   setError(error.message);
        // });
      </script>
      */}
    </div>
  );
}
