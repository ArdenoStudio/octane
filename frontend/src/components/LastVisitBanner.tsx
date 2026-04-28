import { useEffect, useState } from "react";
import { RiArrowDownLine, RiArrowUpLine, RiCloseLine } from "@remixicon/react";
import { api, FUEL_DISPLAY, FUEL_ORDER, FuelId } from "../lib/api";
import { lkr, relativeFromNow } from "../lib/format";

interface StoredPrices {
  [fuel: string]: number;
}

interface PriceChange {
  fuel: FuelId;
  from: number;
  to: number;
  delta: number;
}

const KEY_VISIT = "octane_last_visit";
const KEY_PRICES = "octane_last_prices";

export function LastVisitBanner() {
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

        if (storedPricesRaw && storedVisit) {
          try {
            const stored: StoredPrices = JSON.parse(storedPricesRaw);
            const diffs: PriceChange[] = [];
            FUEL_ORDER.forEach((fuel) => {
              const prev = stored[fuel];
              const curr = current[fuel];
              if (prev !== undefined && curr !== undefined && prev !== curr) {
                diffs.push({ fuel, from: prev, to: curr, delta: curr - prev });
              }
            });
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
                key={c.fuel}
                className="flex items-center gap-1 text-ink-300"
              >
                <span className="text-ink-400">{FUEL_DISPLAY[c.fuel]}</span>
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
