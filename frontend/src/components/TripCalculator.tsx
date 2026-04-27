import { useState } from "react";
import { api, FUEL_DISPLAY, FUEL_ORDER, FuelId, TripResp } from "../lib/api";
import { compactLkr } from "../lib/format";

export function TripCalculator() {
  const [distance, setDistance] = useState("30");
  const [efficiency, setEfficiency] = useState("12");
  const [fuel, setFuel] = useState<FuelId>("petrol_92");
  const [result, setResult] = useState<TripResp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function compute() {
    const d = parseFloat(distance);
    const e = parseFloat(efficiency);
    if (!(d > 0) || !(e > 0)) {
      setError("Enter positive numbers for distance and efficiency.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const r = await api.trip(d, e, fuel);
      setResult(r);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="calc" className="container-x pt-16">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <div className="label">Trip cost</div>
          <h2 className="mt-1 font-display text-3xl font-extrabold tracking-tightest sm:text-4xl">
            How much will it cost you?
          </h2>
          <p className="mt-3 text-ink-300">
            Punch in the distance and your vehicle's fuel efficiency. We do the math
            using today's prices.
          </p>
        </div>

        <div className="card p-5 sm:p-6 lg:col-span-3">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label htmlFor="distance" className="label">Distance (km)</label>
              <input
                id="distance"
                className="input mt-2"
                inputMode="decimal"
                value={distance}
                onChange={(e) => setDistance(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="efficiency" className="label">Efficiency (km/L)</label>
              <input
                id="efficiency"
                className="input mt-2"
                inputMode="decimal"
                value={efficiency}
                onChange={(e) => setEfficiency(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="fuel" className="label">Fuel</label>
              <select
                id="fuel"
                className="input mt-2"
                value={fuel}
                onChange={(e) => setFuel(e.target.value as FuelId)}
              >
                {FUEL_ORDER.map((f) => (
                  <option key={f} value={f}>
                    {FUEL_DISPLAY[f]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <button onClick={compute} className="btn-primary" disabled={loading}>
              {loading ? "Calculating…" : "Calculate"}
            </button>
            {error && <span className="text-sm text-red-300">{error}</span>}
          </div>

          {result && (
            <div className="mt-6 rounded-xl border border-accent/30 bg-accent/5 p-5">
              <div className="label text-accent">This trip costs</div>
              <div className="mt-1 font-display text-4xl font-extrabold tracking-tightest text-ink-100 sm:text-5xl">
                {compactLkr(result.cost_lkr)}
              </div>
              <div className="mt-2 text-sm text-ink-300">
                {result.litres_needed.toFixed(2)} L · LKR{" "}
                {result.price_lkr_per_l.toFixed(2)}/L · {FUEL_DISPLAY[result.fuel_type]}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
