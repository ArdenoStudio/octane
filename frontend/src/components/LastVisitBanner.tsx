import { useEffect, useState } from "react";
import { RiArrowDownLine, RiArrowUpLine, RiCloseLine } from "@remixicon/react";
import { api, EarlySignal, FUEL_ORDER, FuelId } from "../lib/api";
import { useFuelLabel } from "../i18n/LocaleProvider";
import { lkr, relativeFromNow } from "../lib/format";

interface StoredPrices {
  [fuel: string]: number;
}

interface PriceChange {
  fuel: FuelId;
  from: number;
  to: number;
  delta: number;
  /** Media-reported (unconfirmed) when CPC did not move this fuel. */
  viaNews?: boolean;
  /** CPC did not revise this fuel — shown for completeness. */
  unchanged?: boolean;
}

const KEY_VISIT = "octane_last_visit";
const KEY_PRICES = "octane_last_prices";

export function LastVisitBanner() {
  const fuelLabel = useFuelLabel();
  const [changes, setChanges] = useState<PriceChange[]>([]);
  const [since, setSince] = useState<string>("");
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    api
      .latest()
      .then((resp) => {
        const current: StoredPrices = {};
        resp.prices
          .filter((r) => r.source === "cpc")
          .forEach((r) => {
            current[r.fuel_type] = r.price_lkr;
          });

        const storedPricesRaw = localStorage.getItem(KEY_PRICES);
        const storedVisit = localStorage.getItem(KEY_VISIT);
        const early: EarlySignal[] = resp.early_signals ?? [];

        if (storedPricesRaw && storedVisit) {
          try {
            const stored: StoredPrices = JSON.parse(storedPricesRaw);
            const diffs: PriceChange[] = [];
            const changedFuels = new Set<FuelId>();

            // 1) Official CPC moves since last visit — all five fuels.
            FUEL_ORDER.forEach((fuel) => {
              const prev = stored[fuel];
              const curr = current[fuel];
              if (prev !== undefined && curr !== undefined && prev !== curr) {
                diffs.push({ fuel, from: prev, to: curr, delta: curr - prev });
                changedFuels.add(fuel);
              }
            });

            // 2) Also surface media-reported early signals for fuels CPC has
            //    not revised yet (e.g. Petrol 95 still flat officially).
            for (const s of early) {
              const fuel = s.fuel_type as FuelId;
              if (!FUEL_ORDER.includes(fuel) || changedFuels.has(fuel)) continue;
              if (Math.abs(s.delta_lkr) < 0.01) continue;
              diffs.push({
                fuel,
                from: s.cpc_price_lkr,
                to: s.price_lkr,
                delta: s.delta_lkr,
                viaNews: true,
              });
              changedFuels.add(fuel);
            }

            // When anything moved, also list the other fuels as unchanged so
            // Petrol 95 / Super Diesel / Kerosene aren't missing from the strip.
            if (diffs.length > 0) {
              FUEL_ORDER.forEach((fuel) => {
                if (changedFuels.has(fuel)) return;
                const curr = current[fuel];
                if (curr === undefined) return;
                diffs.push({
                  fuel,
                  from: curr,
                  to: curr,
                  delta: 0,
                  unchanged: true,
                });
              });
            }

            // Keep FUEL_ORDER so all five fuels appear in a stable order.
            diffs.sort(
              (a, b) => FUEL_ORDER.indexOf(a.fuel) - FUEL_ORDER.indexOf(b.fuel)
            );

            if (diffs.length > 0) {
              setChanges(diffs);
              setSince(relativeFromNow(storedVisit));
            }
          } catch {
            // stale/corrupt storage — ignore
          }
        }

        // Always update stored snapshot to today
        localStorage.setItem(KEY_PRICES, JSON.stringify(current));
        localStorage.setItem(KEY_VISIT, new Date().toISOString());
      })
      .catch(() => {});
  }, []);

  if (!changes.length || dismissed) return null;

  return (
    <div className="container-x pt-4">
      <div className="flex items-start gap-3 rounded-xl border border-accent/30 bg-accent/5 px-4 py-3">
        <div className="flex-1 text-sm">
          <span className="font-semibold text-ink-200">
            Prices changed since {since}
          </span>
          <div className="mt-1.5 flex flex-wrap gap-x-5 gap-y-1">
            {changes.map((c) => (
              <span
                key={`${c.viaNews ? "news" : c.unchanged ? "flat" : "cpc"}-${c.fuel}`}
                className="flex items-center gap-1 text-ink-300"
              >
                <span className="text-ink-400">{fuelLabel(c.fuel)}</span>
                {c.viaNews && (
                  <span className="rounded bg-amber-500/15 px-1 text-[10px] font-semibold uppercase tracking-wide text-amber-600">
                    News
                  </span>
                )}
                {c.unchanged ? (
                  <span className="text-ink-500">
                    unchanged · {lkr(c.to, { showSymbol: false })}
                  </span>
                ) : (
                  <>
                    {c.delta > 0 ? (
                      <RiArrowUpLine className="size-3.5 text-red-500" />
                    ) : (
                      <RiArrowDownLine className="size-3.5 text-emerald-500" />
                    )}
                    <span
                      className={
                        c.delta > 0
                          ? "font-semibold text-red-600"
                          : "font-semibold text-emerald-600"
                      }
                    >
                      LKR {Math.abs(c.delta).toFixed(2)}
                    </span>
                    <span className="text-ink-400">
                      → {lkr(c.to, { showSymbol: false })}
                    </span>
                  </>
                )}
              </span>
            ))}
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="mt-0.5 rounded-md p-0.5 text-ink-400 transition-colors hover:text-ink-200"
          aria-label="Dismiss"
        >
          <RiCloseLine className="size-4" />
        </button>
      </div>
    </div>
  );
}
