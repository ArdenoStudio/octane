import { useEffect, useMemo, useState } from "react";
import { RiDownload2Line, RiLineChartLine, RiEyeLine, RiEyeOffLine } from "@remixicon/react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, FUEL_ORDER, FuelId, ForecastResp, HistoryPoint, PriceChangeRow, SentimentData } from "../lib/api";
import { useFuelLabel } from "../i18n/LocaleProvider";
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
  const [active, setActive] = useState<Set<FuelId>>(
    () => new Set(["petrol_92", "auto_diesel"])
  );
  const [days, setDays] = useState<number>(365);
  const [mode, setMode] = useState<ChartMode>("daily");

  function switchMode(m: ChartMode) {
    setMode(m);
    if (m === "revisions") setShowForecast(false);
  }

  // Daily mode: per-fuel time-series from /v1/prices/history
  const [series, setSeries] = useState<Record<FuelId, HistoryPoint[]>>({} as Record<FuelId, HistoryPoint[]>);

  // Revisions mode: all actual price change events from /v1/prices/changes
  const [allRevisions, setAllRevisions] = useState<PriceChangeRow[] | null>(null);
  const [revisionsLoading, setRevisionsLoading] = useState(false);
  const [revisionsError, setRevisionsError] = useState<string | null>(null);

  // Forecast / trend overlay
  const [showForecast, setShowForecast] = useState(false);
  const [showConfidenceBands, setShowConfidenceBands] = useState(true);
  const [forecasts, setForecasts] = useState<Record<FuelId, ForecastResp>>({} as Record<FuelId, ForecastResp>);

  // Fetch daily series whenever active fuels, range, or mode changes
  useEffect(() => {
    if (mode !== "daily") return;
    Promise.all(
      Array.from(active).map((f) => api.history(f, days).then((r) => [f, r.points] as const))
    )
      .then((entries) => {
        const next: Record<FuelId, HistoryPoint[]> = { ...series };
        for (const [f, pts] of entries) next[f] = pts;
        setSeries(next);
      })
      .catch(() => undefined);
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

  // Fetch all revision events once when first switching to revisions mode
  useEffect(() => {
    if (mode !== "revisions" || allRevisions !== null) return;
    setRevisionsLoading(true);
    setRevisionsError(null);
    api
      .changes(5000)
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
    const conf80ByFuel: Partial<Record<FuelId, Map<string, [number, number]>>> = {};
    const conf95ByFuel: Partial<Record<FuelId, Map<string, [number, number]>>> = {};

    for (const f of active) {
      const fc = forecasts[f];
      if (!fc) continue;
      regByFuel[f] = new Map(fc.regression_points.map((p) => [p.date, p.price_lkr]));
      fwdByFuel[f] = new Map(fc.forecast_points.map((p) => [p.date, p.price_lkr]));
      aiFwdByFuel[f] = new Map((fc.ai_forecast_points ?? []).map((p) => [p.date, p.price_lkr]));
      conf80ByFuel[f] = new Map(
        fc.forecast_points
          .filter((p) => p.conf_80_lower != null && p.conf_80_upper != null)
          .map((p) => [p.date, [p.conf_80_lower!, p.conf_80_upper!]])
      );
      conf95ByFuel[f] = new Map(
        fc.forecast_points
          .filter((p) => p.conf_95_lower != null && p.conf_95_upper != null)
          .map((p) => [p.date, [p.conf_95_lower!, p.conf_95_upper!]])
      );
      fc.regression_points.forEach((p) => allDates.add(p.date));
      fc.forecast_points.forEach((p) => allDates.add(p.date));
      (fc.ai_forecast_points ?? []).forEach((p) => allDates.add(p.date));
    }

    return Array.from(allDates)
      .sort()
      .map((d) => {
        const row: Record<string, string | number | [number, number]> = { date: d };
        for (const f of active) {
          const reg = regByFuel[f]?.get(d);
          const fwd = fwdByFuel[f]?.get(d);
          const aiFwd = aiFwdByFuel[f]?.get(d);
          const conf80 = conf80ByFuel[f]?.get(d);
          const conf95 = conf95ByFuel[f]?.get(d);
          if (reg != null) row[`${f}_reg`] = reg;
          if (fwd != null) row[`${f}_fwd`] = fwd;
          if (aiFwd != null) row[`${f}_ai_fwd`] = aiFwd;
          if (conf80 != null) row[`${f}_conf80`] = conf80;
          if (conf95 != null) row[`${f}_conf95`] = conf95;
        }
        return row;
      });
  }, [showForecast, forecasts, active]);

  const chartData = useMemo(() => {
    if (mode === "revisions" && allRevisions) {
      // Show only dates when prices actually changed — no interpolation
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - days);
      const cutoffStr = cutoff.toISOString().slice(0, 10);

      const priceMap: Partial<Record<FuelId, Map<string, number>>> = {};
      const dateSet = new Set<string>();
      for (const f of active) priceMap[f] = new Map();

      for (const c of allRevisions) {
        if (!active.has(c.fuel_type as FuelId)) continue;
        if (c.recorded_at < cutoffStr) continue;
        dateSet.add(c.recorded_at);
        priceMap[c.fuel_type as FuelId]!.set(c.recorded_at, c.price_lkr);
      }

      return Array.from(dateSet)
        .sort()
        .map((d) => {
          const row: Record<string, string | number> = { date: d };
          for (const f of active) {
            const v = priceMap[f]!.get(d);
            if (v != null) row[f] = v;
          }
          return row;
        });
    }

    // Daily mode — merge per-fuel series by date
    const dateSet = new Set<string>();
    Object.values(series).forEach((arr) => arr?.forEach((p) => dateSet.add(p.recorded_at)));
    const dates = Array.from(dateSet).sort();
    const indices: Partial<Record<FuelId, Map<string, number>>> = {};
    (Object.keys(series) as FuelId[]).forEach((f) => {
      indices[f] = new Map(series[f]!.map((p) => [p.recorded_at, p.price_lkr]));
    });
    return dates.map((d) => {
      const row: Record<string, string | number> = { date: d };
      (Object.keys(indices) as FuelId[]).forEach((f) => {
        const v = indices[f]!.get(d);
        if (v != null) row[f] = v;
      });
      return row;
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
    const map = new Map<string, Record<string, string | number | [number, number]>>();
    for (const row of chartData) map.set(row.date as string, { ...row });
    for (const row of chartDataWithForecast) {
      const existing = map.get(row.date as string) ?? { date: row.date };
      map.set(row.date as string, { ...existing, ...row });
    }
    const merged = Array.from(map.values()).sort((a, b) =>
      (a.date as string).localeCompare(b.date as string)
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

        // Confidence bands (apply same offset)
        const conf80 = next[`${f}_conf80`] as [number, number] | undefined;
        if (conf80 != null) {
          if (i > anchor) {
            next[`${f}_conf80`] = [conf80[0] + off, conf80[1] + off];
          } else {
            delete next[`${f}_conf80`];
          }
        }

        const conf95 = next[`${f}_conf95`] as [number, number] | undefined;
        if (conf95 != null) {
          if (i > anchor) {
            next[`${f}_conf95`] = [conf95[0] + off, conf95[1] + off];
          } else {
            delete next[`${f}_conf95`];
          }
        }
      }
      return next;
    });
  }, [chartData, chartDataWithForecast, active]);

  const isLoading = mode === "revisions" && revisionsLoading;
  const hasRevisionsError = mode === "revisions" && !!revisionsError;
  const hasSentiment = sentiment !== null;
  const hasAiForecast = showForecast && Object.values(forecasts).some(
    (f) => (f.ai_forecast_points ?? []).length > 0
  );

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
            {/* Mode: Daily interpolated vs Revisions only */}
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
                {(["daily", "revisions"] as const).map((m) => (
                  <label
                    key={m}
                    className={`relative z-10 inline-flex h-full cursor-pointer select-none items-center justify-center px-3 capitalize transition-colors ${
                      mode === m ? "text-ink-950" : "text-ink-400 hover:text-ink-200"
                    }`}
                  >
                    {m}
                    <RadioGroupItem value={m} className="sr-only" />
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

            {/* Confidence bands toggle — only when forecast is shown */}
            {showForecast && (
              <button
                onClick={() => setShowConfidenceBands((v) => !v)}
                title="Toggle confidence interval bands"
                className={`flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs font-semibold transition ${
                  showConfidenceBands
                    ? "border-purple-500 bg-purple-500/10 text-purple-400"
                    : "border-ink-700 text-ink-400 hover:border-ink-600 hover:text-ink-200"
                }`}
              >
                {showConfidenceBands ? (
                  <RiEyeLine className="size-3.5" />
                ) : (
                  <RiEyeOffLine className="size-3.5" />
                )}
                CI Bands
              </button>
            )}

            <a
              href={api.historyCsvUrl(Array.from(active), days)}
              download
              title="Download CSV"
              className="flex items-center gap-1 rounded-lg border border-ink-700 px-2.5 py-1 text-xs font-semibold text-ink-400 transition hover:border-ink-600 hover:text-ink-200"
            >
              <RiDownload2Line className="size-3.5" />
              CSV
            </a>
            <a
              href={api.historyJsonUrl(Array.from(active), days)}
              download
              title="Download JSON"
              className="flex items-center gap-1 rounded-lg border border-ink-700 px-2.5 py-1 text-xs font-semibold text-ink-400 transition hover:border-ink-600 hover:text-ink-200"
            >
              <RiDownload2Line className="size-3.5" />
              JSON
            </a>
          </div>
        </div>

        {mode === "revisions" && (
          <p className="mt-2 text-xs text-ink-500">
            Only dates when prices actually changed — no daily interpolation.
          </p>
        )}
        {showForecast && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <p className="text-xs text-ink-500">
              <span className="font-semibold text-accent">Trend</span>: dashed line projects 60 days ahead using linear regression
              {showConfidenceBands && (
                <> with <span className="font-semibold text-purple-400">80%</span> and <span className="font-semibold text-purple-300/60">95%</span> confidence bands</>
              )}
              {" — "}
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
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={mergedData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
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
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const items = payload.filter((p) => {
                      const key = p.dataKey as string;
                      return FUEL_ORDER.includes(key as FuelId) || key.endsWith("_ai_fwd");
                    });
                    if (!items.length) return null;
                    return (
                      <div style={{ background: "#fff", border: "1px solid #e4e4e7", borderRadius: 12, fontSize: 12, padding: "8px 12px", boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
                        <div style={{ color: "#71717a", marginBottom: 6 }}>{label}</div>
                        {items.map((p) => {
                          const key = p.dataKey as string;
                          const isAI = key.endsWith("_ai_fwd");
                          const fuel = (isAI ? key.replace("_ai_fwd", "") : key) as FuelId;
                          return (
                            <div key={key} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                              <span style={{ color: p.color, fontSize: 8 }}>●</span>
                              <span style={{ color: "#3f3f46" }}>
                                {fuelLabel(fuel)}{isAI ? <span style={{ color: "#a1a1aa" }}> · AI</span> : null}
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
                    type={mode === "revisions" ? "stepAfter" : "monotone"}
                    dataKey={f}
                    stroke={COLORS[f]}
                    strokeWidth={2}
                    dot={mode === "revisions" ? { r: 3, fill: COLORS[f], strokeWidth: 0 } : false}
                    connectNulls
                    isAnimationActive={false}
                  />
                ))}

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

                {/* 95% Confidence band — lighter */}
                {showForecast && showConfidenceBands && Array.from(active).map((f) =>
                  forecasts[f] ? (
                    <Area
                      key={`${f}_conf95`}
                      type="linear"
                      dataKey={`${f}_conf95`}
                      fill={COLORS[f]}
                      fillOpacity={0.08}
                      stroke="none"
                      isAnimationActive={false}
                      legendType="none"
                    />
                  ) : null
                )}

                {/* 80% Confidence band — darker */}
                {showForecast && showConfidenceBands && Array.from(active).map((f) =>
                  forecasts[f] ? (
                    <Area
                      key={`${f}_conf80`}
                      type="linear"
                      dataKey={`${f}_conf80`}
                      fill={COLORS[f]}
                      fillOpacity={0.15}
                      stroke="none"
                      isAnimationActive={false}
                      legendType="none"
                    />
                  ) : null
                )}
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </section>
  );
}
