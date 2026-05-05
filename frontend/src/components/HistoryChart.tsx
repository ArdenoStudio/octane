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
import { api, FUEL_DISPLAY, FUEL_ORDER, FuelId, ForecastResp, HistoryPoint, PriceChangeRow } from "../lib/api";
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

export function HistoryChart() {
  const [active, setActive] = useState<Set<FuelId>>(
    () => new Set(["petrol_92", "auto_diesel"])
  );
  const [days, setDays] = useState<number>(365);
  const [mode, setMode] = useState<ChartMode>("daily");

  // Daily mode: per-fuel time-series from /v1/prices/history
  const [series, setSeries] = useState<Record<FuelId, HistoryPoint[]>>({} as Record<FuelId, HistoryPoint[]>);

  // Revisions mode: all actual price change events from /v1/prices/changes
  const [allRevisions, setAllRevisions] = useState<PriceChangeRow[] | null>(null);
  const [revisionsLoading, setRevisionsLoading] = useState(false);
  const [revisionsError, setRevisionsError] = useState<string | null>(null);

  // Forecast / trend overlay
  const [showForecast, setShowForecast] = useState(false);
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
        api.forecast(f, Math.min(days, 365), 90).then((r) => [f, r] as const)
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

  // Merge forecast regression + forward projection into chart data
  const chartDataWithForecast = useMemo(() => {
    if (!showForecast) return null;

    const allDates = new Set<string>();
    const regByFuel: Partial<Record<FuelId, Map<string, number>>> = {};
    const fwdByFuel: Partial<Record<FuelId, Map<string, number>>> = {};

    for (const f of active) {
      const fc = forecasts[f];
      if (!fc) continue;
      regByFuel[f] = new Map(fc.regression_points.map((p) => [p.date, p.price_lkr]));
      fwdByFuel[f] = new Map(fc.forecast_points.map((p) => [p.date, p.price_lkr]));
      fc.regression_points.forEach((p) => allDates.add(p.date));
      fc.forecast_points.forEach((p) => allDates.add(p.date));
    }

    return Array.from(allDates)
      .sort()
      .map((d) => {
        const row: Record<string, string | number> = { date: d };
        for (const f of active) {
          const reg = regByFuel[f]?.get(d);
          const fwd = fwdByFuel[f]?.get(d);
          if (reg != null) row[`${f}_reg`] = reg;
          if (fwd != null) row[`${f}_fwd`] = fwd;
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
    const map = new Map<string, Record<string, string | number>>();
    for (const row of chartData) map.set(row.date as string, { ...row });
    for (const row of chartDataWithForecast) {
      const existing = map.get(row.date as string) ?? { date: row.date };
      map.set(row.date as string, { ...existing, ...row });
    }
    return Array.from(map.values()).sort((a, b) =>
      (a.date as string).localeCompare(b.date as string)
    );
  }, [chartData, chartDataWithForecast]);

  const isLoading = mode === "revisions" && revisionsLoading;
  const hasRevisionsError = mode === "revisions" && !!revisionsError;

  return (
    <section id="history" className="container-x pt-16">
      <div className="card p-5 sm:p-7">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label">Price history</div>
            <h2 className="mt-1 font-display text-2xl font-extrabold tracking-tightest sm:text-3xl">
              Every revision since the records begin.
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {/* Mode: Daily interpolated vs Revisions only */}
            <div className="inline-flex h-8 rounded-lg bg-ink-900 p-0.5">
              <RadioGroup
                value={mode}
                onValueChange={(v) => setMode(v as ChartMode)}
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

            {/* Trend / forecast toggle */}
            <button
              onClick={() => setShowForecast((v) => !v)}
              title="Toggle 90-day trend forecast"
              className={`flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs font-semibold transition ${
                showForecast
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-ink-700 text-ink-400 hover:border-ink-600 hover:text-ink-200"
              }`}
            >
              <RiLineChartLine className="size-3.5" />
              Trend
            </button>

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
          <p className="mt-2 text-xs text-ink-500">
            <span className="font-semibold text-accent">Trend</span>: dashed line shows a linear regression fit over the selected period. Projected 90 days ahead — for indicative purposes only.
            {Object.keys(forecasts).length > 0 && (() => {
              const f = Array.from(active).find((k) => forecasts[k]?.r_squared != null);
              if (!f) return null;
              const r2 = forecasts[f]?.r_squared;
              return r2 != null ? <> R² = {(r2 * 100).toFixed(0)}%.</> : null;
            })()}
          </p>
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
                {FUEL_DISPLAY[f]}
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
              <LineChart data={mergedData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#e4e4e7" strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d) => String(d).slice(0, 7)}
                  stroke="#a1a1aa"
                  fontSize={11}
                  minTickGap={32}
                />
                <YAxis
                  stroke="#a1a1aa"
                  fontSize={11}
                  tickFormatter={(v) => String(v)}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  contentStyle={{
                    background: "#ffffff",
                    border: "1px solid #e4e4e7",
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#71717a" }}
                  formatter={(value: number, name: string) => [
                    `LKR ${value.toFixed(2)}`,
                    FUEL_DISPLAY[name as FuelId] ?? name,
                  ]}
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

                {/* Forecast: regression line over history */}
                {showForecast && Array.from(active).map((f) =>
                  forecasts[f] ? (
                    <Line
                      key={`${f}_reg`}
                      type="linear"
                      dataKey={`${f}_reg`}
                      stroke={COLORS[f]}
                      strokeWidth={1.5}
                      strokeDasharray="6 3"
                      dot={false}
                      connectNulls
                      isAnimationActive={false}
                      legendType="none"
                    />
                  ) : null
                )}

                {/* Forecast: forward projection (90 days ahead) */}
                {showForecast && Array.from(active).map((f) =>
                  forecasts[f] ? (
                    <Line
                      key={`${f}_fwd`}
                      type="linear"
                      dataKey={`${f}_fwd`}
                      stroke={COLORS[f]}
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      strokeOpacity={0.6}
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
