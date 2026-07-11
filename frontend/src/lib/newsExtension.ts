import type { EarlySignal, FuelId } from "./api";
import { FUEL_ORDER } from "./api";

export type ChartRow = Record<string, string | number | boolean>;

/** dataKey suffix for the dashed media-report extension segment. */
export function extKey(fuel: FuelId): string {
  return `${fuel}_ext`;
}

function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export interface NewsExtensionOptions {
  /** ISO date — do not inject anchors before this (selected chart window). */
  rangeStart?: string | null;
  today?: string;
}

/**
 * Overlay a dashed "extension" of the official CPC line toward a media-reported
 * price. When CPC revises (early signal clears), callers pass no signals and the
 * extension disappears — one graph, not two modes.
 */
export function applyNewsExtensions(
  rows: ChartRow[],
  signals: EarlySignal[],
  active: Iterable<FuelId>,
  options: NewsExtensionOptions | string = {}
): ChartRow[] {
  // Back-compat: older call sites passed `today` as the 4th arg.
  const opts: NewsExtensionOptions =
    typeof options === "string" ? { today: options } : options;
  const today = opts.today ?? new Date().toISOString().slice(0, 10);
  const rangeStart = opts.rangeStart ?? null;

  const activeSet = active instanceof Set ? active : new Set(active);
  const pending = signals.filter(
    (s) =>
      activeSet.has(s.fuel_type) &&
      Math.abs(s.delta_lkr) >= 0.01 &&
      FUEL_ORDER.includes(s.fuel_type)
  );
  if (pending.length === 0) return rows;

  const byDate = new Map<string, ChartRow>();
  for (const row of rows) {
    byDate.set(String(row.date), { ...row });
  }

  // First visible date in the current series (fallback clamp).
  const firstRowDate =
    rows.length > 0 ? String([...rows].sort((a, b) => String(a.date).localeCompare(String(b.date)))[0].date) : null;
  const clampStart = rangeStart ?? firstRowDate;

  for (const s of pending) {
    const f = s.fuel_type;
    let startDate = s.cpc_recorded_at;
    if (clampStart && startDate < clampStart) startDate = clampStart;

    let endDate = s.recorded_at > startDate ? s.recorded_at : today;
    if (endDate <= startDate) endDate = today;
    // Same-day CPC + news: still show a short stub so the dashed tip is visible.
    if (endDate <= startDate) endDate = addDays(startDate, 1);

    const startRow = byDate.get(startDate) ?? { date: startDate };
    startRow[extKey(f)] = s.cpc_price_lkr;
    if (startRow[f] == null) startRow[f] = s.cpc_price_lkr;
    byDate.set(startDate, startRow);

    // Dense fill so the dashed segment is continuous across intermediate dates.
    const dates = Array.from(byDate.keys()).sort();
    for (const d of dates) {
      if (d > startDate && d < endDate) {
        const mid = byDate.get(d)!;
        mid[extKey(f)] = s.cpc_price_lkr;
      }
    }

    const endRow = byDate.get(endDate) ?? { date: endDate };
    endRow[extKey(f)] = s.price_lkr;
    byDate.set(endDate, endRow);
  }

  return Array.from(byDate.values()).sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  );
}
