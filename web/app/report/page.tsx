"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { downloadPdf, fetchHtml } from "@/lib/api";

export default function ReportPage() {
  const [html, setHtml] = useState("");
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    fetchHtml("/report")
      .then(setHtml)
      .catch((err) => setError(err.message));
  }, []);

  async function handleDownload() {
    setDownloading(true);
    setError("");
    try {
      const blob = await downloadPdf("/report.pdf");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "friction-finder-report.pdf";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export PDF");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <AppShell>
      <section className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-card">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-ink">COO Report Preview</h2>
          <p className="text-sm text-slate-600">Live server-side HTML report with downloadable PDF export.</p>
        </div>
        <button type="button" className="btn-primary" onClick={handleDownload} disabled={downloading}>
          {downloading ? "Exporting..." : "Download PDF"}
        </button>
      </section>

      {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}

      <section className="card overflow-hidden">
        <iframe title="Report Preview" srcDoc={html} className="h-[78vh] w-full border-0" />
      </section>
    </AppShell>
  );
}
