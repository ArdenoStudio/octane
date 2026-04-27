import { useEffect, useState } from "react";
import { api, FUEL_DISPLAY, FUEL_ORDER, FuelId, PriceRow } from "../lib/api";
import { lkr, relativeFromNow, shortDate } from "../lib/format";

const ACCENT_BY_FUEL: Record<FuelId, string> = {
  petrol_92: "from-amber-500/30 to-amber-500/0",
  petrol_95: "from-orange-500/30 to-orange-500/0",
  auto_diesel: "from-emerald-500/25 to-emerald-500/0",
  super_diesel: "from-cyan-500/25 to-cyan-500/0",
  kerosene: "from-violet-500/25 to-violet-500/0",
};

export function PriceStrip() {
  const [rows, setRows] = useState<PriceRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .latest()
      .then((r) => setRows(r.prices))
      .catch((e) => setError(String(e)));
  }, []);

  const cpcByFuel: Partial<Record<FuelId, PriceRow>> = {};
  rows?.forEach((r) => {
    if (r.source === "cpc") cpcByFuel[r.fuel_type] = r;
  });

  const lastRevision = rows
    ? rows
        .filter((r) => r.source === "cpc")
        .map((r) => r.recorded_at)
        .sort()
        .pop()
    : null;

  return (
    <section id="prices" className="container-x pt-10 sm:pt-14">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">Live prices · CPC</div>
          <h1 className="mt-1 font-display text-3xl font-extrabold tracking-tightest sm:text-4xl">
            Sri Lanka fuel prices, today.
          </h1>
        </div>
        {lastRevision && (
          <div className="text-right text-sm text-ink-400">
            Last revision <span className="text-ink-200">{shortDate(lastRevision)}</span>
            <span className="ml-1 text-ink-400">· {relativeFromNow(lastRevision)}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-6 rounded-xl border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-200">
          Couldn't load prices. The API may be offline. <span className="text-red-300/70">{error}</span>
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {FUEL_ORDER.map((fuel) => {
          const row = cpcByFuel[fuel];
          return (
            <div
              key={fuel}
              className={`card relative overflow-hidden p-5`}
            >
              <div
                aria-hidden
                className={`pointer-events-none absolute -inset-x-10 -top-20 h-40 bg-gradient-to-b blur-2xl ${ACCENT_BY_FUEL[fuel]}`}
              />
              <div className="relative">
                <div className="label">{FUEL_DISPLAY[fuel]}</div>
                <div className="mt-2 font-display text-3xl font-extrabold tracking-tightest text-ink-100">
                  {row ? lkr(row.price_lkr, { showSymbol: false }) : "—"}
                </div>
                <div className="mt-1 text-xs text-ink-400">
                  {row ? `LKR · ${shortDate(row.recorded_at)}` : "Awaiting data"}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
