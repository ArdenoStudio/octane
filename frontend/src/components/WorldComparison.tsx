import { useEffect, useState } from "react";
import { api, ComparisonResp, FUEL_DISPLAY, FUEL_ORDER, FuelId } from "../lib/api";

const FLAGS: Record<string, string> = {
  "Sri Lanka": "🇱🇰",
  India: "🇮🇳",
  Pakistan: "🇵🇰",
  Bangladesh: "🇧🇩",
  Nepal: "🇳🇵",
  Maldives: "🇲🇻",
  World: "🌐",
};

export function WorldComparison() {
  const [fuel, setFuel] = useState<FuelId>("petrol_95");
  const [data, setData] = useState<ComparisonResp | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    api.worldComparison(fuel).then(setData).catch((e) => setError(String(e)));
  }, [fuel]);

  const delta = data?.delta_vs_world_pct;
  const direction =
    delta == null ? "" : delta > 0 ? "above" : delta < 0 ? "below" : "in line with";
  const magnitude = delta == null ? null : Math.abs(delta);

  return (
    <section className="container-x pt-16">
      <div className="card p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="label">vs the world</div>
          <div className="flex flex-wrap gap-1">
            {FUEL_ORDER.map((f) => (
              <button
                key={f}
                onClick={() => setFuel(f)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                  fuel === f
                    ? "bg-accent text-ink-950"
                    : "border border-ink-700 text-ink-300 hover:bg-ink-800"
                }`}
              >
                {FUEL_DISPLAY[f]}
              </button>
            ))}
          </div>
        </div>

        <p className="mt-4 max-w-3xl font-display text-2xl font-bold leading-tight tracking-tightest sm:text-3xl">
          {error || !data ? (
            <span className="text-ink-400">Loading comparison…</span>
          ) : magnitude == null ? (
            <>
              World comparison data is{" "}
              <span className="text-ink-400">not yet available.</span>
            </>
          ) : (
            <>
              Sri Lanka {FUEL_DISPLAY[fuel].toLowerCase()} is{" "}
              <span className="text-accent">{magnitude.toFixed(1)}% {direction}</span>{" "}
              the world average.
            </>
          )}
        </p>

        {data && (
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
            {[
              { country: "Sri Lanka", price_usd: data.sri_lanka.price_usd ?? 0 },
              ...data.neighbors,
              data.world_average_usd != null
                ? { country: "World", price_usd: data.world_average_usd }
                : null,
            ]
              .filter(Boolean)
              .map((row, i) => {
                const r = row as { country: string; price_usd: number };
                return (
                  <div
                    key={`${r.country}-${i}`}
                    className="rounded-xl border border-ink-800 bg-ink-900/50 p-3"
                  >
                    <div className="flex items-center gap-1.5 text-sm text-ink-300">
                      <span aria-hidden>{FLAGS[r.country] ?? "🏳"}</span>
                      <span>{r.country}</span>
                    </div>
                    <div className="mt-1 font-mono text-base font-semibold text-ink-100">
                      ${r.price_usd?.toFixed(2)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-ink-400">
                      USD / litre
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </section>
  );
}
