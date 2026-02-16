"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { downloadPdf, fetchHtml } from "@/lib/api";

const CURRENCY_KEY = "ff_report_currency";
const HOURLY_RATE_KEY = "ff_report_hourly_rate";
const DEFAULT_CURRENCY: "GBP" | "USD" | "EUR" = "GBP";
const DEFAULT_RATE = 30;
const MIN_RATE = 10;
const MAX_RATE = 300;

const RATE_PRESETS = [
  { id: "ops_analyst", label: "Ops Analyst / Coordinator (conservative)", rate: 25 },
  { id: "ops_manager", label: "Ops Manager", rate: 40 },
  { id: "senior_ops", label: "Senior Ops / Program Manager", rate: 60 },
  { id: "head_ops", label: "Head of Ops / Director", rate: 85 },
  { id: "blended_conservative", label: "Fully-loaded blended rate (conservative)", rate: 50 },
] as const;

type Currency = "GBP" | "USD" | "EUR";
type PresetId = (typeof RATE_PRESETS)[number]["id"] | "custom";

function clampRate(value: number): number {
  if (!Number.isFinite(value)) return DEFAULT_RATE;
  return Math.min(MAX_RATE, Math.max(MIN_RATE, Math.round(value)));
}

export default function ReportPage() {
  const [html, setHtml] = useState("");
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [currency, setCurrency] = useState<Currency>(DEFAULT_CURRENCY);
  const [preset, setPreset] = useState<PresetId>("blended_conservative");
  const [customRate, setCustomRate] = useState<string>(String(DEFAULT_RATE));

  const effectiveRate = useMemo(() => {
    if (preset === "custom") return clampRate(Number(customRate));
    const selected = RATE_PRESETS.find((item) => item.id === preset);
    return selected ? selected.rate : DEFAULT_RATE;
  }, [customRate, preset]);

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const queryCurrency = query.get("currency");
    const queryRate = Number(query.get("rate"));

    const storedCurrency = window.localStorage.getItem(CURRENCY_KEY);
    const storedRate = Number(window.localStorage.getItem(HOURLY_RATE_KEY));

    const initialCurrency: Currency =
      queryCurrency === "GBP" || queryCurrency === "USD" || queryCurrency === "EUR"
        ? queryCurrency
        : storedCurrency === "GBP" || storedCurrency === "USD" || storedCurrency === "EUR"
          ? storedCurrency
          : DEFAULT_CURRENCY;
    const numericRate = clampRate(Number.isFinite(queryRate) ? queryRate : storedRate);

    const matchedPreset = RATE_PRESETS.find((item) => item.rate === numericRate);
    setCurrency(initialCurrency);
    setCustomRate(String(numericRate));
    setPreset(matchedPreset ? matchedPreset.id : "custom");
  }, []);

  function reportPath(prefix: "/report.html" | "/report.pdf"): string {
    const params = new URLSearchParams({
      currency,
      rate: String(effectiveRate),
      hourly_rate: String(effectiveRate),
    });
    return `${prefix}?${params.toString()}`;
  }

  function syncUrlAndStorage() {
    window.localStorage.setItem(CURRENCY_KEY, currency);
    window.localStorage.setItem(HOURLY_RATE_KEY, String(effectiveRate));
    const url = new URL(window.location.href);
    url.searchParams.set("currency", currency);
    url.searchParams.set("rate", String(effectiveRate));
    window.history.replaceState({}, "", `${url.pathname}?${url.searchParams.toString()}`);
  }

  async function loadPreview() {
    setLoadingPreview(true);
    setError("");
    try {
      const content = await fetchHtml(reportPath("/report.html"));
      setHtml(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report preview");
    } finally {
      setLoadingPreview(false);
    }
  }

  useEffect(() => {
    syncUrlAndStorage();
    void loadPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currency, preset, customRate]);

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
            <p className="text-sm text-slate-600">Board-ready report preview and PDF export with deterministic ROI assumptions.</p>
          </div>
          <button type="button" className="btn-primary" onClick={handleDownload} disabled={downloading}>
            {downloading ? "Exporting..." : "Download PDF"}
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <label className="flex flex-col gap-1 text-sm text-slate-700">
            <span className="text-xs uppercase tracking-[0.12em] text-slate-500">Currency</span>
            <select className="input" value={currency} onChange={(event) => setCurrency(event.target.value as Currency)}>
              <option value="GBP">GBP</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm text-slate-700">
            <span className="text-xs uppercase tracking-[0.12em] text-slate-500">Hourly Rate Preset</span>
            <select className="input" value={preset} onChange={(event) => setPreset(event.target.value as PresetId)}>
              {RATE_PRESETS.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label} ({item.rate}/hr)
                </option>
              ))}
              <option value="custom">Custom...</option>
            </select>
          </label>

          {preset === "custom" ? (
            <label className="flex flex-col gap-1 text-sm text-slate-700">
              <span className="text-xs uppercase tracking-[0.12em] text-slate-500">Custom Hourly Rate</span>
              <input
                className="input"
                type="number"
                min={MIN_RATE}
                max={MAX_RATE}
                value={customRate}
                onChange={(event) => setCustomRate(event.target.value)}
              />
            </label>
          ) : (
            <div className="flex items-end">
              <p className="text-xs text-slate-500">Effective rate: {effectiveRate}/hr</p>
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
