import type { FuelId } from "./api";
import { FUEL_ORDER } from "./api";

export type ChartRow = Record<string, string | number>;

/**
 * Merge sparse per-fuel revision points onto a shared date axis and
 * forward-fill each fuel so CPC step prices stay flat until the next change.
 * Without this, Recharts `connectNulls` draws misleading slopes across gaps.
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
