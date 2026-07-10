import type { EarlySignal, FuelId } from "./api";
import { FUEL_ORDER } from "./api";

export type ChartRow = Record<string, string | number>;

/** dataKey suffix for the dashed media-report extension segment. */
export function extKey(fuel: FuelId): string {
  return `${fuel}_ext`;
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
  today: string = new Date().toISOString().slice(0, 10)
): ChartRow[] {
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

  for (const s of pending) {
    const f = s.fuel_type;
    const startDate = s.cpc_recorded_at;
    let endDate = s.recorded_at > startDate ? s.recorded_at : today;
    if (endDate <= startDate) endDate = today;
    if (endDate <= startDate) continue;

    const startRow = byDate.get(startDate) ?? { date: startDate };
    startRow[extKey(f)] = s.cpc_price_lkr;
    if (startRow[f] == null) startRow[f] = s.cpc_price_lkr;
    byDate.set(startDate, startRow);

    const endRow = byDate.get(endDate) ?? { date: endDate };
    endRow[extKey(f)] = s.price_lkr;
    byDate.set(endDate, endRow);
  }

  return Array.from(byDate.values()).sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  );
}
