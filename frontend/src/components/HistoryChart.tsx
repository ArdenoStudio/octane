import { useEffect, useMemo, useState } from "react";
import { RiDownload2Line, RiLineChartLine } from "@remixicon/react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  EarlySignal,
  FUEL_ORDER,
  FuelId,
  ForecastResp,
  HistoryPoint,
  PriceChangeRow,
  resolveEarlySignals,
  SentimentData,
} from "../lib/api";
import { useFuelLabel } from "../i18n/LocaleProvider";
import { lkr } from "../lib/format";
import { buildForwardFilledSeries, expandToDailyCalendar } from "../lib/chartSeries";
import { applyNewsExtensions, extKey } from "../lib/newsExtension";
import { RadioGroup, RadioGroupItem } from "./ui/radio-group";

const COLORS: Record<FuelId, string> = {
  petrol_92: "#f59e0b",
  petrol_95: "#fb923c",
  auto_diesel: "#10b981",
  super_diesel: "#06b6d4",
  kerosene: "#a78bfa",
};

const RANGES = [
  { label: "1Y", days: 365 },
  { label: "5Y", days: 365 * 5 },
  { label: "10Y", days: 365 * 10 },
  { label: "All", days: 36500 },
];

type ChartMode = "daily" | "revisions";

function SentimentBadge({ sentiment }: { sentiment: SentimentData }) {
  const arrow = sentiment.direction === "up" ? "↑" : sentiment.direction === "down" ? "↓" : "→";
  const label = sentiment.direction === "up" ? "Bullish" : sentiment.direction === "down" ? "Bearish" : "Neutral";
  const colorClass =
    sentiment.direction === "up"
      ? "text-red-400 border-red-400/30 bg-red-400/10"
      : sentiment.direction === "down"
      ? "text-emerald-400 border-emerald-400/30 bg-emerald-400/10"
      : "text-ink-400 border-ink-600 bg-ink-800/40";

  return (
    <span
      title={`${sentiment.summary} (${sentiment.headlines_analyzed} headlines analysed)`}
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-semibold ${colorClass}`}
    >
      <span>{arrow}</span>
      <span>AI {label}</span>
      <span className="opacity-60">·</span>
      <span className="opacity-80">{(sentiment.confidence * 100).toFixed(0)}%</span>
    </span>
  );
}

export function HistoryChart() {
  const fuelLabel = useFuelLabel();
  // Default: all five fuels so Petrol 95 / Super Diesel / Kerosene are visible
  // without an extra click (users can still deselect).
  const [active, setActive] = useState<Set<FuelId>>(() => new Set(FUEL_ORDER));
  const [days, setDays] = useState<number>(365);
  const [mode, setMode] = useState<ChartMode>("daily");
  // Pending media reports (only when they differ from CPC) — not a chart mode.
  const [earlySignals, setEarlySignals] = useState<EarlySignal[]>([]);

  function switchMode(m: ChartMode) {
    setMode(m);
    if (m === "revisions") setShowForecast(false);
  }

  // Daily mode: per-fuel time-series from /v1/prices/history (official CPC only)
  const [series, setSeries] = useState<Record<FuelId, HistoryPoint[]>>({} as Record<FuelId, HistoryPoint[]>);

  // Revisions mode: all actual price change events from /v1/prices/changes
  const [allRevisions, setAllRevisions] = useState<PriceChangeRow[] | null>(null);
  const [revisionsLoading, setRevisionsLoading] = useState(false);
  const [revisionsError, setRevisionsError] = useState<string | null>(null);

  // Forecast / trend overlay
  const [showForecast, setShowForecast] = useState(false);
  const [forecasts, setForecasts] = useState<Record<FuelId, ForecastResp>>({} as Record<FuelId, ForecastResp>);

  useEffect(() => {
    let cancelled = false;
    api
      .latest()
      .then((resp) => {
        if (!cancelled) setEarlySignals(resolveEarlySignals(resp));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch daily series whenever active fuels, range, or mode changes
  useEffect(() => {
    if (mode !== "daily") return;
    let cancelled = false;
    Promise.all(
      Array.from(active).map((f) =>
        api.history(f, days, "cpc").then((r) => [f, r.points] as const)
      )
    )
      .then((entries) => {
        if (cancelled) return;
        const next = {} as Record<FuelId, HistoryPoint[]>;
        for (const [f, pts] of entries) next[f] = pts;
        setSeries(next);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days, mode, Array.from(active).join(",")]);

  // Fetch forecasts for active fuels when trend overlay is toggled on
  useEffect(() => {
    if (!showForecast) return;
    const fuelsNeeded = Array.from(active).filter((f) => !forecasts[f]);
    if (fuelsNeeded.length === 0) return;
    Promise.all(
      fuelsNeeded.map((f) =>
        api.forecast(f, Math.min(days, 365), 60).then((r) => [f, r] as const)
      )
    ).then((entries) => {
      const next = { ...forecasts };
      for (const [f, r] of entries) next[f] = r;
      setForecasts(next);
    }).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showForecast, Array.from(active).join(",")]);

  // Fetch revision events when switching to revisions mode
  useEffect(() => {
    if (mode !== "revisions" || allRevisions !== null) return;
    setRevisionsLoading(true);
    setRevisionsError(null);
    api
      .changes(5000, "cpc")
      .then((r) => setAllRevisions(r.changes))
      .catch((e: unknown) => {
        setRevisionsError(String(e));
        setAllRevisions([]);
      })
      .finally(() => setRevisionsLoading(false));
  }, [mode, allRevisions]);

  // Pull the sentiment snapshot off the first available forecast result
  const sentiment: SentimentData | null = useMemo(() => {
    if (!showForecast) return null;
    for (const f of FUEL_ORDER) {
      const s = forecasts[f]?.sentiment;
      if (s) return s;
    }
    return null;
  }, [showForecast, forecasts]);

  // Merge forecast regression + forward projection into chart data
  const chartDataWithForecast = useMemo(() => {
    if (!showForecast) return null;

    const allDates = new Set<string>();
    const regByFuel: Partial<Record<FuelId, Map<string, number>>> = {};
    const fwdByFuel: Partial<Record<FuelId, Map<string, number>>> = {};
    const aiFwdByFuel: Partial<Record<FuelId, Map<string, number>>> = {};

    for (const f of active) {
      const fc = forecasts[f];
      if (!fc) continue;
      regByFuel[f] = new Map(fc.regression_points.map((p) => [p.date, p.price_lkr]));
      fwdByFuel[f] = new Map(fc.forecast_points.map((p) => [p.date, p.price_lkr]));
      aiFwdByFuel[f] = new Map((fc.ai_forecast_points ?? []).map((p) => [p.date, p.price_lkr]));
      fc.regression_points.forEach((p) => allDates.add(p.date));
      fc.forecast_points.forEach((p) => allDates.add(p.date));
      (fc.ai_forecast_points ?? []).forEach((p) => allDates.add(p.date));
    }

    return Array.from(allDates)
      .sort()
      .map((d) => {
        const row: Record<string, string | number> = { date: d };
        for (const f of active) {
          const reg = regByFuel[f]?.get(d);
          const fwd = fwdByFuel[f]?.get(d);
          const aiFwd = aiFwdByFuel[f]?.get(d);
          if (reg != null) row[`${f}_reg`] = reg;
          if (fwd != null) row[`${f}_fwd`] = fwd;
          if (aiFwd != null) row[`${f}_ai_fwd`] = aiFwd;
        }
        return row;
      });
  }, [showForecast, forecasts, active]);

  const chartData = useMemo(() => {
    if (mode === "revisions" && allRevisions) {
      // Revision events only — still forward-fill so multi-fuel rows don't
      // leave gaps that Recharts would slope across.
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);
      const cutoffStr = cutoff.toISOString().slice(0, 10);

      const byFuel: Partial<Record<FuelId, { recorded_at: string; price_lkr: number }[]>> = {};
      for (const f of active) byFuel[f] = [];

      for (const c of allRevisions) {
        if (!active.has(c.fuel_type as FuelId)) continue;
        if (c.recorded_at < cutoffStr) continue;
        byFuel[c.fuel_type as FuelId]!.push({
          recorded_at: c.recorded_at,
          price_lkr: c.price_lkr,
        });
      }
      return buildForwardFilledSeries(byFuel, active);
    }

    // Timeline: forward-fill revisions, then expand to one point per calendar
    // day so plateaus and drops are visually obvious (day-proportional X).
    const filled = buildForwardFilledSeries(series, active);
    return expandToDailyCalendar(filled, {
      endDate: new Date().toISOString().slice(0, 10),
      fuels: Array.from(active),
    });
  }, [mode, series, allRevisions, active, days]);

  function toggle(f: FuelId) {
    const next = new Set(active);
    if (next.has(f)) next.delete(f);
    else next.add(f);
    if (next.size === 0) next.add(f);
    setActive(next);
  }

  // Merge actual + forecast points by date for the combined chart
  const mergedData = useMemo(() => {
    if (!chartDataWithForecast) return chartData;
    const map = new Map<string, Record<string, string | number | boolean>>();
    for (const row of chartData) map.set(String(row.date), { ...row });
    for (const row of chartDataWithForecast) {
      const existing = map.get(String(row.date)) ?? { date: row.date };
      map.set(String(row.date), { ...existing, ...row });
    }
    const merged = Array.from(map.values()).sort((a, b) =>
      String(a.date).localeCompare(String(b.date))
    );

    // Anchor each fuel's trend lines to its last actual price and hide any
    // projected points that fall inside the historical period.
    const offsets: Partial<Record<FuelId, number>> = {};
    const anchorIndices: Partial<Record<FuelId, number>> = {};
    for (const f of active) {
      for (let i = merged.length - 1; i >= 0; i--) {
        const row = merged[i];
        if (row[f] != null && row[`${f}_reg`] != null) {
          offsets[f] = (row[f] as number) - (row[`${f}_reg`] as number);
          anchorIndices[f] = i;
          break;
        }
      }
    }

    return merged.map((row, i) => {
      const next = { ...row };
      for (const f of active) {
        const off = offsets[f];
        const anchor = anchorIndices[f];
        if (off == null || anchor == null) continue;

        // Linear regression forward projection
        if (i === anchor) {
          next[`${f}_fwd`] = next[f] as number;
        } else if (next[`${f}_fwd`] != null) {
          if (i > anchor) {
            next[`${f}_fwd`] = (next[`${f}_fwd`] as number) + off;
          } else {
            delete next[`${f}_fwd`];
          }
        }

        // AI forward projection (same offset/anchor logic)
        if (i === anchor) {
          next[`${f}_ai_fwd`] = next[f] as number;
        } else if (next[`${f}_ai_fwd`] != null) {
          if (i > anchor) {
            next[`${f}_ai_fwd`] = (next[`${f}_ai_fwd`] as number) + off;
          } else {
            delete next[`${f}_ai_fwd`];
          }
        }
      }
      return next;
    });
  }, [chartData, chartDataWithForecast, active]);

  const pendingSignals = useMemo(
    () => earlySignals.filter((s) => Math.abs(s.delta_lkr) >= 0.01),
    [earlySignals]
  );

  const rangeStart = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    return cutoff.toISOString().slice(0, 10);
  }, [days]);

  // Single graph: solid CPC + dashed media extension that clears when CPC revises.
  const displayData = useMemo(
    () =>
      applyNewsExtensions(mergedData, pendingSignals, active, {
        rangeStart,
        today: new Date().toISOString().slice(0, 10),
      }),
    [mergedData, pendingSignals, active, rangeStart]
  );

  const chartRemountKey = `${mode}-${days}-${Array.from(active).join(",")}-${displayData.length}-${String(displayData.at(-1)?.date ?? "")}`;

  const yDomain = useMemo((): [number | "auto", number | "auto"] | [(n: number) => number, (n: number) => number] => {
    let min = Infinity;
    let max = -Infinity;
    for (const row of displayData) {
      for (const f of active) {
        const v = row[f];
        if (typeof v === "number") {
          min = Math.min(min, v);
          max = Math.max(max, v);
        }
        const ext = row[extKey(f)];
        if (typeof ext === "number") {
          min = Math.min(min, ext);
          max = Math.max(max, ext);
        }
      }
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) return ["auto", "auto"];
    const pad = Math.max(5, (max - min) * 0.08);
    return [Math.floor(min - pad), Math.ceil(max + pad)];
  }, [displayData, active]);

  const isLoading = mode === "revisions" && revisionsLoading;
  const hasRevisionsError = mode === "revisions" && !!revisionsError;
  const hasSentiment = sentiment !== null;
  const hasAiForecast = showForecast && Object.values(forecasts).some(
    (f) => (f.ai_forecast_points ?? []).length > 0
  );
  const hasChartPoints = displayData.length > 0;

  return (
    <section id="history" className="container-x pt-16">
      <div className="card p-5 sm:p-7">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label">Price history</div>
            <h2 className="mt-1 font-display text-2xl font-bold tracking-tightest sm:text-3xl">
              Every revision since the records begin.
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {/* Mode: forward-filled timeline vs revision events only */}
            <div className="inline-flex h-8 rounded-lg bg-ink-900 p-0.5">
              <RadioGroup
                value={mode}
                onValueChange={(v) => switchMode(v as ChartMode)}
                className="relative inline-grid grid-cols-2 items-center gap-0 text-xs font-semibold"
              >
                <div
                  aria-hidden
                  className="absolute inset-y-0 w-1/2 rounded-md bg-ink-100 transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
                  style={{
                    transform: `translateX(${mode === "daily" ? "0%" : "100%"})`,
                    boxShadow:
                      "0 0 6px rgba(0,0,0,0.03), 0 2px 6px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.08)",
                  }}
                />
                {(
                  [
                    { id: "daily" as const, label: "Timeline" },
                    { id: "revisions" as const, label: "Revisions" },
                  ] as const
                ).map((m) => (
                  <label
                    key={m.id}
                    className={`relative z-10 inline-flex h-full cursor-pointer select-none items-center justify-center px-3 transition-colors ${
                      mode === m.id ? "text-ink-950" : "text-ink-400 hover:text-ink-200"
                    }`}
                  >
                    {m.label}
                    <RadioGroupItem value={m.id} className="sr-only" />
                  </label>
                ))}
              </RadioGroup>
            </div>

            {/* Range picker */}
            <div className="inline-flex h-8 rounded-lg bg-ink-900 p-0.5">
              <RadioGroup
                value={String(days)}
                onValueChange={(v) => setDays(Number(v))}
                className="relative inline-grid grid-cols-4 items-center gap-0 text-xs font-semibold"
              >
                <div
                  aria-hidden
                  className="absolute inset-y-0 w-1/4 rounded-md bg-ink-100 transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
                  style={{
                    transform: `translateX(${RANGES.findIndex((r) => r.days === days) * 100}%)`,
                    boxShadow:
                      "0 0 6px rgba(0,0,0,0.03), 0 2px 6px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.08)",
                  }}
                />
                {RANGES.map((r) => (
                  <label
                    key={r.label}
                    className={`relative z-10 inline-flex h-full min-w-8 cursor-pointer select-none items-center justify-center px-3 transition-colors ${
                      days === r.days ? "text-ink-950" : "text-ink-400 hover:text-ink-200"
                    }`}
                  >
                    {r.label}
                    <RadioGroupItem value={String(r.days)} className="sr-only" />
                  </label>
                ))}
              </RadioGroup>
            </div>

            {/* Trend / forecast toggle — daily mode only */}
            {mode === "daily" && (
              <button
                onClick={() => setShowForecast((v) => !v)}
                title="Toggle 60-day trend forecast"
                className={`flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs font-semibold transition ${
                  showForecast
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-ink-700 text-ink-400 hover:border-ink-600 hover:text-ink-200"
                }`}
              >
                <RiLineChartLine className="size-3.5" />
                Trend
              </button>
            )}

            <a
              href={api.historyCsvUrl(Array.from(active), days, "cpc")}
              download
              title="Download CSV"
              className="flex items-center gap-1 rounded-lg border border-ink-700 px-2.5 py-1 text-xs font-semibold text-ink-400 transition hover:border-ink-600 hover:text-ink-200"
            >
              <RiDownload2Line className="size-3.5" />
              CSV
            </a>
            <a
              href={api.historyJsonUrl(Array.from(active), days, "cpc")}
              download
              title="Download JSON"
              className="flex items-center gap-1 rounded-lg border border-ink-700 px-2.5 py-1 text-xs font-semibold text-ink-400 transition hover:border-ink-600 hover:text-ink-200"
            >
              <RiDownload2Line className="size-3.5" />
              JSON
            </a>
          </div>
        </div>

        {pendingSignals.length > 0 && (
          <div className="mt-3 rounded-lg border border-amber-500/25 bg-amber-500/5 px-3 py-2 text-xs text-amber-200/90">
            <span className="font-semibold text-amber-300">Dashed = media report</span>
            <span className="text-ink-500">
              {" "}
              · extends the official line until CPC revises, then it drops off ·{" "}
            </span>
            {pendingSignals.map((s, i) => {
              const up = s.delta_lkr > 0;
              return (
                <span key={`${s.source}-${s.fuel_type}`} className="text-ink-300">
                  {i > 0 ? " · " : ""}
                  {fuelLabel(s.fuel_type)}{" "}
                  <span className="font-semibold tabular-nums text-ink-100">
                    {lkr(s.price_lkr, { showSymbol: false })}
                  </span>
                  <span className={up ? "text-red-400" : "text-emerald-400"}>
                    {" "}
                    ({up ? "+" : ""}
                    {lkr(s.delta_lkr, { showSymbol: false })})
                  </span>
                </span>
              );
            })}
          </div>
        )}
        {mode === "revisions" && (
          <p className="mt-2 text-xs text-ink-500">
            Only dates when prices actually changed — no daily interpolation.
          </p>
        )}
        {showForecast && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <p className="text-xs text-ink-500">
              <span className="font-semibold text-accent">Trend</span>: dashed line projects 60 days ahead using linear regression —{" "}
              {hasAiForecast && (
                <>bright dashed line is the <span className="font-semibold text-ink-300">AI forecast</span> (Groq · Llama 3.1) based on news sentiment — </>
              )}
              for indicative purposes only.
              {Object.keys(forecasts).length > 0 && (() => {
                const f = Array.from(active).find((k) => forecasts[k]?.r_squared != null);
                if (!f) return null;
                const r2 = forecasts[f]?.r_squared;
                return r2 != null ? <> R² = {(r2 * 100).toFixed(0)}%.</> : null;
              })()}
            </p>
            {hasSentiment && <SentimentBadge sentiment={sentiment!} />}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          {FUEL_ORDER.map((f) => {
            const on = active.has(f);
            return (
              <button
                key={f}
                onClick={() => toggle(f)}
                className={`flex items-center gap-2 rounded-lg border px-2.5 py-1 text-xs font-medium transition ${
                  on
                    ? "border-ink-700 bg-white text-ink-200 shadow-sm"
                    : "border-ink-800 text-ink-600 hover:border-ink-700 hover:text-ink-400"
                }`}
              >
                <span
                  aria-hidden
                  className="h-2 w-2 rounded-full"
                  style={{ background: on ? COLORS[f] : "#d4d4d8" }}
                />
                {fuelLabel(f)}
              </button>
            );
          })}
        </div>

        <div className="mt-4 h-72 sm:h-96">
          {isLoading ? (
            <div className="flex h-full items-center justify-center text-sm text-ink-500">
              Loading revision history…
            </div>
          ) : hasRevisionsError ? (
            <div className="flex h-full items-center justify-center text-sm text-red-400">
              Couldn't load revision data. Try refreshing.
            </div>
          ) : !hasChartPoints ? (
            <div className="flex h-full flex-col items-center justify-center gap-1 px-6 text-center text-sm text-ink-500">
              <span>No price points in this range.</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                key={chartRemountKey}
                data={displayData}
                margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#e4e4e7" strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d) => String(d).slice(0, 7)}
                  stroke="#a1a1aa"
                  fontSize={11}
                  minTickGap={70}
                />
                <YAxis
                  stroke="#a1a1aa"
                  fontSize={11}
                  tickFormatter={(v) => String(v)}
                  domain={yDomain}
                  allowDataOverflow={false}
                />
                <Tooltip
                  cursor={{ stroke: "#a1a1aa", strokeDasharray: "3 3" }}
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const items = payload.filter((p) => {
                      const key = p.dataKey as string;
                      return (
                        FUEL_ORDER.includes(key as FuelId) ||
                        key.endsWith("_ext") ||
                        key.endsWith("_ai_fwd")
                      );
                    });
                    if (!items.length) return null;
                    return (
                      <div style={{ background: "#fff", border: "1px solid #e4e4e7", borderRadius: 12, fontSize: 12, padding: "8px 12px", boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
                        <div style={{ color: "#71717a", marginBottom: 6 }}>{label}</div>
                        {items.map((p) => {
                          const key = p.dataKey as string;
                          const isAI = key.endsWith("_ai_fwd");
                          const isExt = key.endsWith("_ext");
                          const fuel = (
                            isAI ? key.replace("_ai_fwd", "") : isExt ? key.replace("_ext", "") : key
                          ) as FuelId;
                          return (
                            <div key={key} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                              <span style={{ color: p.color, fontSize: 8 }}>{isExt ? "◌" : "●"}</span>
                              <span style={{ color: "#3f3f46" }}>
                                {fuelLabel(fuel)}
                                {isExt ? (
                                  <span style={{ color: "#d97706" }}> · media</span>
                                ) : isAI ? (
                                  <span style={{ color: "#a1a1aa" }}> · AI</span>
                                ) : null}
                              </span>
                              <span style={{ marginLeft: "auto", paddingLeft: 12, fontWeight: 500 }}>
                                LKR {(p.value as number).toFixed(2)}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    );
                  }}
                />
                {mode === "revisions" &&
                  chartData.map((d) => (
                    <ReferenceLine
                      key={d.date as string}
                      x={d.date as string}
                      stroke="#d4d4d8"
                      strokeDasharray="2 4"
                    />
                  ))}
                {Array.from(active).map((f) => (
                  <Line
                    key={f}
                    type="stepAfter"
                    dataKey={f}
                    stroke={COLORS[f]}
                    strokeWidth={2.25}
                    dot={
                      mode === "revisions"
                        ? { r: 3.5, fill: COLORS[f], strokeWidth: 0 }
                        : (props: {
                            cx?: number;
                            cy?: number;
                            payload?: { _revision?: boolean; date?: string };
                          }) => {
                            const { cx, cy, payload } = props;
                            if (cx == null || cy == null || !payload?._revision) {
                              return <g />;
                            }
                            return (
                              <circle
                                cx={cx}
                                cy={cy}
                                r={4}
                                fill={COLORS[f]}
                                stroke="#fff"
                                strokeWidth={1.5}
                              />
                            );
                          }
                    }
                    activeDot={{ r: 6, strokeWidth: 2, stroke: "#fff", fill: COLORS[f] }}
                    connectNulls
                    isAnimationActive={false}
                  />
                ))}

                {/* Media early-signal extension — same colour, dashed; clears when CPC revises */}
                {pendingSignals.length > 0 &&
                  Array.from(active).map((f) =>
                    pendingSignals.some((s) => s.fuel_type === f) ? (
                      <Line
                        key={extKey(f)}
                        type="stepAfter"
                        dataKey={extKey(f)}
                        stroke={COLORS[f]}
                        strokeWidth={2.5}
                        strokeDasharray="7 4"
                        strokeOpacity={0.9}
                        dot={{ r: 3.5, fill: COLORS[f], strokeWidth: 0 }}
                        activeDot={{ r: 5, strokeWidth: 0, fill: COLORS[f] }}
                        connectNulls
                        isAnimationActive={false}
                        legendType="none"
                      />
                    ) : null
                  )}

                {/* Linear regression forward projection — dim dashed */}
                {showForecast && Array.from(active).map((f) =>
                  forecasts[f] ? (
                    <Line
                      key={`${f}_fwd`}
                      type="linear"
                      dataKey={`${f}_fwd`}
                      stroke={COLORS[f]}
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      strokeOpacity={0.35}
                      dot={false}
                      connectNulls
                      isAnimationActive={false}
                      legendType="none"
                    />
                  ) : null
                )}

                {/* AI-adjusted forward projection — brighter dashed */}
                {showForecast && hasAiForecast && Array.from(active).map((f) =>
                  (forecasts[f]?.ai_forecast_points ?? []).length > 0 ? (
                    <Line
                      key={`${f}_ai_fwd`}
                      type="linear"
                      dataKey={`${f}_ai_fwd`}
                      stroke={COLORS[f]}
                      strokeWidth={2}
                      strokeDasharray="6 3"
                      strokeOpacity={0.75}
                      dot={false}
                      connectNulls
                      isAnimationActive={false}
                      legendType="none"
                    />
                  ) : null
                )}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </section>
  );
}
