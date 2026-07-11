import type { FuelId } from "./api";
import { FUEL_ORDER } from "./api";

export type ChartRow = Record<string, string | number | boolean>;

function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function eachDay(start: string, end: string): string[] {
  if (end < start) return [];
  const out: string[] = [];
  let cur = start;
  // Hard cap avoids pathological ranges (e.g. "All" with bad data).
  for (let i = 0; i < 4000 && cur <= end; i++) {
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
 * Expand a forward-filled revision series to one row per calendar day.
 * That makes long flat stretches and sharp revision steps obvious on the
 * chart (categorical X spacing becomes day-proportional).
 */
export function expandToDailyCalendar(
  rows: ChartRow[],
  opts: { endDate?: string; fuels?: FuelId[] } = {}
): ChartRow[] {
  if (rows.length === 0) return rows;
  const sorted = [...rows].sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  );
  const start = String(sorted[0].date);
  const lastData = String(sorted[sorted.length - 1].date);
  const end = opts.endDate && opts.endDate > lastData ? opts.endDate : lastData;
  const byDate = new Map(sorted.map((r) => [String(r.date), r]));
  const fuels =
    opts.fuels ??
    FUEL_ORDER.filter((f) => sorted.some((r) => typeof r[f] === "number"));

  const last: Partial<Record<FuelId, number>> = {};
  const out: ChartRow[] = [];

  for (const d of eachDay(start, end)) {
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
