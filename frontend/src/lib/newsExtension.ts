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
 * price. Only the last CPC anchor and the media tip are set — no dense mid-fill
 * along the official price (that was stacking duplicate dots on the chart).
 *
 * The start anchor is always snapped to an existing chart row that already has
 * this fuel's price, so we never inject an orphan high-price point after a
 * multi-year gap (which made connectNulls draw a vertical spike on "All").
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

  const sortedDates = Array.from(byDate.keys()).sort();
  if (sortedDates.length === 0) return rows;
  const firstRowDate = sortedDates[0];
  const lastRowDate = sortedDates[sortedDates.length - 1];
  const clampStart = rangeStart ?? firstRowDate;

  for (const s of pending) {
    const f = s.fuel_type;
    let preferredStart = s.cpc_recorded_at;
    if (clampStart && preferredStart < clampStart) preferredStart = clampStart;

    // Snap to the latest existing row on/before the CPC date that already has
    // this fuel — never invent a lone point decades after the series ends.
    const snapped =
      [...sortedDates]
        .reverse()
        .find((d) => d <= preferredStart && typeof byDate.get(d)?.[f] === "number") ??
      [...sortedDates]
        .reverse()
        .find((d) => typeof byDate.get(d)?.[f] === "number") ??
      lastRowDate;

    const startDate = snapped;
    const startRow = byDate.get(startDate)!;
    const cpcAnchor =
      typeof startRow[f] === "number" ? (startRow[f] as number) : s.cpc_price_lkr;

    let endDate = s.recorded_at > startDate ? s.recorded_at : today;
    if (endDate <= startDate) endDate = today;
    if (endDate <= startDate) endDate = addDays(startDate, 1);
    // Keep the tip close to the visible series end (avoid a far orphan date).
    if (endDate < startDate) endDate = addDays(startDate, 1);

    startRow[extKey(f)] = cpcAnchor;
    byDate.set(startDate, startRow);

    const endRow = byDate.get(endDate) ?? { date: endDate };
    // Carry forward official price onto the tip day so the solid line reaches
    // the tip and the dashed segment only shows the media delta.
    if (endRow[f] == null) endRow[f] = cpcAnchor;
    endRow[extKey(f)] = s.price_lkr;
    byDate.set(endDate, endRow);
  }

  return Array.from(byDate.values()).sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  );
}
