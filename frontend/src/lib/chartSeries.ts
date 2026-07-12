import type { FuelId } from "./api";
import { FUEL_ORDER } from "./api";

export type ChartRow = Record<string, string | number | boolean>;

/** Daily expansion above this span is skipped — silent 4k truncation used to
 *  drop recent years on "All" and then media tips re-injected a 2026 spike. */
export const DAILY_EXPAND_MAX_DAYS = 800;

function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function daySpan(start: string, end: string): number {
  const a = Date.parse(`${start}T12:00:00Z`);
  const b = Date.parse(`${end}T12:00:00Z`);
  if (!Number.isFinite(a) || !Number.isFinite(b) || b < a) return 0;
  return Math.round((b - a) / 86_400_000) + 1;
}

function eachDay(start: string, end: string, maxDays: number): string[] {
  if (end < start) return [];
  const out: string[] = [];
  let cur = start;
  for (let i = 0; i < maxDays && cur <= end; i++) {
    out.push(cur);
    cur = addDays(cur, 1);
  }
  return out;
}

/**
 * Merge sparse per-fuel revision points onto a shared date axis and
 * forward-fill each fuel so CPC step prices stay flat until the next change.
 */
export function buildForwardFilledSeries(
  series: Partial<Record<FuelId, { recorded_at: string; price_lkr: number }[]>>,
  active: Iterable<FuelId>
): ChartRow[] {
  const activeFuels = FUEL_ORDER.filter((f) => {
    for (const a of active) if (a === f) return true;
    return false;
  });

  const dateSet = new Set<string>();
  const indices: Partial<Record<FuelId, Map<string, number>>> = {};
  for (const f of activeFuels) {
    const pts = series[f] ?? [];
    indices[f] = new Map(pts.map((p) => [p.recorded_at, p.price_lkr]));
    for (const p of pts) dateSet.add(p.recorded_at);
  }

  const dates = Array.from(dateSet).sort();
  const last: Partial<Record<FuelId, number>> = {};

  return dates.map((d) => {
    const row: ChartRow = { date: d };
    for (const f of activeFuels) {
      const v = indices[f]?.get(d);
      if (v != null) last[f] = v;
      if (last[f] != null) row[f] = last[f]!;
    }
    return row;
  });
}

/**
 * Shared date axis with each fuel set only on its own revision days (no
 * forward-fill). Optional endDate anchors the last known price so lines reach
 * "today" without inventing mid-hold stairs.
 */
export function buildSparseSeries(
  series: Partial<Record<FuelId, { recorded_at: string; price_lkr: number }[]>>,
  active: Iterable<FuelId>,
  opts: { endDate?: string } = {}
): ChartRow[] {
  const activeFuels = FUEL_ORDER.filter((f) => {
    for (const a of active) if (a === f) return true;
    return false;
  });

  const dateSet = new Set<string>();
  const indices: Partial<Record<FuelId, Map<string, number>>> = {};
  const last: Partial<Record<FuelId, number>> = {};
  for (const f of activeFuels) {
    const pts = [...(series[f] ?? [])].sort((a, b) =>
      a.recorded_at.localeCompare(b.recorded_at)
    );
    indices[f] = new Map(pts.map((p) => [p.recorded_at, p.price_lkr]));
    for (const p of pts) {
      dateSet.add(p.recorded_at);
      last[f] = p.price_lkr;
    }
  }

  if (opts.endDate) dateSet.add(opts.endDate);

  const dates = Array.from(dateSet).sort();
  return dates.map((d) => {
    const row: ChartRow = { date: d };
    for (const f of activeFuels) {
      const v = indices[f]?.get(d);
      if (v != null) {
        row[f] = v;
      } else if (opts.endDate && d === opts.endDate && last[f] != null) {
        // Terminal hold only — keeps media tips / "today" aligned.
        row[f] = last[f]!;
      }
    }
    return row;
  });
}

/**
 * Ensure a sparse forward-filled series reaches `endDate` so media tips and
 * "today" line up with the last official price (no connectNulls spike).
 */
export function extendSparseToEnd(
  rows: ChartRow[],
  endDate: string,
  fuels: FuelId[]
): ChartRow[] {
  if (rows.length === 0) return rows;
  const sorted = [...rows].sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  );
  const last = sorted[sorted.length - 1];
  const lastDate = String(last.date);
  // Mark every sparse revision row so short-range callers can still tip dots.
  const marked = sorted.map((r) => ({ ...r, _revision: true }));
  if (endDate <= lastDate) return marked;

  const tail: ChartRow = { date: endDate };
  for (const f of fuels) {
    if (typeof last[f] === "number") tail[f] = last[f]!;
  }
  return [...marked, tail];
}

/**
 * Expand a forward-filled revision series to one row per calendar day when
 * the span is short enough. Longer spans stay sparse (revision dates only)
 * and are extended to endDate — never silently truncated mid-history.
 */
export function expandToDailyCalendar(
  rows: ChartRow[],
  opts: { endDate?: string; fuels?: FuelId[]; maxDays?: number } = {}
): ChartRow[] {
  if (rows.length === 0) return rows;
  const sorted = [...rows].sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  );
  const start = String(sorted[0].date);
  const lastData = String(sorted[sorted.length - 1].date);
  const end = opts.endDate && opts.endDate > lastData ? opts.endDate : lastData;
  const fuels =
    opts.fuels ??
    FUEL_ORDER.filter((f) => sorted.some((r) => typeof r[f] === "number"));
  const maxDays = opts.maxDays ?? DAILY_EXPAND_MAX_DAYS;
  const span = daySpan(start, end);

  if (span > maxDays) {
    return extendSparseToEnd(sorted, end, fuels);
  }

  const byDate = new Map(sorted.map((r) => [String(r.date), r]));
  const last: Partial<Record<FuelId, number>> = {};
  const out: ChartRow[] = [];

  for (const d of eachDay(start, end, maxDays + 1)) {
    const src = byDate.get(d);
    const row: ChartRow = { date: d };
    let anyRevision = false;
    for (const f of fuels) {
      if (src && typeof src[f] === "number") {
        const next = src[f] as number;
        if (last[f] != null && last[f] !== next) anyRevision = true;
        if (last[f] == null) anyRevision = true; // first point
        last[f] = next;
      }
      if (last[f] != null) row[f] = last[f]!;
      // Preserve extension / forecast keys on exact source days.
      if (src) {
        for (const [k, v] of Object.entries(src)) {
          if (k === "date" || FUEL_ORDER.includes(k as FuelId)) continue;
          if (typeof v === "number" || typeof v === "boolean") row[k] = v;
        }
      }
    }
    if (anyRevision) row._revision = true;
    out.push(row);
  }
  return out;
}
