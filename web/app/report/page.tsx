"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { downloadPdf, fetchHtml } from "@/lib/api";

const CURRENCY_KEY = "ff_report_currency";
const HOURLY_RATE_KEY = "ff_report_hourly_rate";
const RATE_PRESETS = [30, 45, 60, 75, 100, 125, 150];
const DEFAULT_CURRENCY: "GBP" | "USD" | "EUR" = "GBP";
const DEFAULT_RATE = 60;

export default function ReportPage() {
  const [html, setHtml] = useState("");
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [currency, setCurrency] = useState<"GBP" | "USD" | "EUR">(DEFAULT_CURRENCY);
  const [rateOption, setRateOption] = useState<string>(String(DEFAULT_RATE));
  const [customRate, setCustomRate] = useState<string>(String(DEFAULT_RATE));

  useEffect(() => {
    const storedCurrency = window.localStorage.getItem(CURRENCY_KEY);
    const storedRateRaw = window.localStorage.getItem(HOURLY_RATE_KEY);
    const storedRate = storedRateRaw ? Number(storedRateRaw) : DEFAULT_RATE;
    const validRate = Number.isFinite(storedRate) ? Math.min(500, Math.max(10, storedRate)) : DEFAULT_RATE;

    if (storedCurrency === "GBP" || storedCurrency === "USD" || storedCurrency === "EUR") {
      setCurrency(storedCurrency);
    }
    setCustomRate(String(validRate));
    setRateOption(RATE_PRESETS.includes(validRate) ? String(validRate) : "custom");
  }, []);

  function currentHourlyRate(): number {
    const value = rateOption === "custom" ? Number(customRate) : Number(rateOption);
    if (!Number.isFinite(value)) return DEFAULT_RATE;
    return Math.min(500, Math.max(10, value));
  }

  function reportPath(prefix: "/report" | "/report.pdf"): string {
    const params = new URLSearchParams({
      hourly_rate: String(currentHourlyRate()),
      currency,
    });
    return `${prefix}?${params.toString()}`;
  }

  async function loadPreview() {
    setLoadingPreview(true);
    setError("");
    try {
      const content = await fetchHtml(reportPath("/report"));
      setHtml(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report preview");
    } finally {
      setLoadingPreview(false);
    }
  }

  useEffect(() => {
    const hourlyRate = currentHourlyRate();
    window.localStorage.setItem(CURRENCY_KEY, currency);
    window.localStorage.setItem(HOURLY_RATE_KEY, String(hourlyRate));
    void loadPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currency, rateOption, customRate]);

  function reportFileName(): string {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, "0");
    const dd = String(now.getDate()).padStart(2, "0");
    return `friction-finder-report-${yyyy}${mm}${dd}.pdf`;
  }

  async function handleDownload() {
    setDownloading(true);
    setError("");
    try {
      const blob = await downloadPdf(reportPath("/report.pdf"));
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = reportFileName();
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
      <section className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-card">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-ink">COO Report Preview</h2>
            <p className="text-sm text-slate-600">Live server-side HTML report with downloadable PDF export.</p>
          </div>
          <button type="button" className="btn-primary" onClick={handleDownload} disabled={downloading}>
            {downloading ? "Exporting..." : "Download PDF"}
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <label className="flex flex-col gap-1 text-sm text-slate-700">
            <span className="text-xs uppercase tracking-[0.12em] text-slate-500">Currency</span>
            <select className="input" value={currency} onChange={(event) => setCurrency(event.target.value as "GBP" | "USD" | "EUR")}>
              <option value="GBP">GBP</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm text-slate-700">
            <span className="text-xs uppercase tracking-[0.12em] text-slate-500">Hourly Rate</span>
            <select className="input" value={rateOption} onChange={(event) => setRateOption(event.target.value)}>
              {RATE_PRESETS.map((rate) => (
                <option key={rate} value={String(rate)}>
                  {rate}
                </option>
              ))}
              <option value="custom">Custom</option>
            </select>
          </label>

          {rateOption === "custom" ? (
            <label className="flex flex-col gap-1 text-sm text-slate-700">
              <span className="text-xs uppercase tracking-[0.12em] text-slate-500">Custom Rate</span>
              <input
                className="input"
                type="number"
                min={10}
                max={500}
                value={customRate}
                onChange={(event) => setCustomRate(event.target.value)}
              />
            </label>
          ) : (
            <div className="flex items-end">
              <p className="text-xs text-slate-500">Using conservative default of 60/hour unless changed.</p>
            </div>
          )}
        </div>
      </section>

      {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}

      <section className="card overflow-hidden">
        {loadingPreview ? <div className="p-4 text-sm text-slate-500">Refreshing report preview...</div> : null}
        <iframe title="Report Preview" srcDoc={html} className="h-[78vh] w-full border-0" />
      </section>
    </AppShell>
  );
}
