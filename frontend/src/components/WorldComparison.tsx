import { useEffect, useState } from "react"
import { api, ComparisonResp, FUEL_DISPLAY, FUEL_ORDER, FuelId } from "../lib/api"
import { shortDate } from "../lib/format"

const FLAGS: Record<string, string> = {
  "Sri Lanka": "🇱🇰",
  India: "🇮🇳",
  Pakistan: "🇵🇰",
  Bangladesh: "🇧🇩",
  Nepal: "🇳🇵",
  Maldives: "🇲🇻",
  World: "🌐",
}

export function WorldComparison() {
  const [fuel, setFuel] = useState<FuelId>("petrol_95")
  const [data, setData] = useState<ComparisonResp | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setData(null)
    setError(null)
    api.worldComparison(fuel).then(setData).catch((e) => setError(String(e)))
  }, [fuel])

  const delta = data?.delta_vs_world_pct
  const isBelow = delta != null && delta < 0
  const direction =
    delta == null ? "" : delta > 0 ? "above" : delta < 0 ? "below" : "at"
  const magnitude = delta == null ? null : Math.abs(delta)

  const countryRows = data
    ? [
        { country: "Sri Lanka", price_usd: data.sri_lanka.price_usd ?? 0, isSelf: true },
        ...data.neighbors.map((n) => ({ ...n, isSelf: false })),
        data.world_average_usd != null
          ? { country: "World", price_usd: data.world_average_usd, isSelf: false }
          : null,
      ].filter(Boolean) as { country: string; price_usd: number; isSelf: boolean }[]
    : []

  const maxPrice = countryRows.length
    ? Math.max(...countryRows.map((r) => r.price_usd)) * 1.15
    : 1

  return (
    <section id="world" className="container-x pt-16">
      <div className="overflow-hidden rounded-3xl border border-ink-800 bg-white shadow-sm">

        {/* Top accent line */}
        <div className="h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent" />

        {/* Header */}
        <div className="px-6 pt-10 pb-8 text-center sm:px-10">

          {/* Badge */}
          <div className="inline-block rounded-full border border-accent/30 bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-amber-700">
            vs the world
          </div>

          {/* Headline */}
          <div className="mt-5">
            {!data && !error && (
              <div className="h-16 animate-pulse rounded-xl bg-ink-900/40 mx-auto max-w-xs" />
            )}
            {error && (
              <p className="text-lg text-red-500">Could not load comparison data</p>
            )}
            {data && magnitude != null && (
              <h2 className="text-5xl font-extrabold tracking-tighter text-ink-100 sm:text-6xl">
                <span className={isBelow ? "text-emerald-600" : "text-red-500"}>
                  {magnitude.toFixed(1)}%{" "}
                </span>
                <span className="text-ink-200">{direction} world average</span>
              </h2>
            )}
            {data && magnitude == null && (
              <h2 className="text-4xl font-extrabold tracking-tighter text-ink-200">
                Sri Lanka vs the world
              </h2>
            )}
          </div>

          <p className="mt-2 text-sm text-ink-400">
            {FUEL_DISPLAY[fuel]} · price per litre in USD
          </p>

          {/* Fuel selector */}
          <div className="mt-5 flex flex-wrap justify-center gap-1.5">
            {FUEL_ORDER.map((f) => (
              <button
                key={f}
                onClick={() => setFuel(f)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  fuel === f
                    ? "bg-accent text-zinc-900 shadow-sm"
                    : "border border-ink-800 text-ink-400 hover:border-ink-700 hover:text-ink-200"
                }`}
              >
                {FUEL_DISPLAY[f]}
              </button>
            ))}
          </div>
        </div>

        {/* Divider */}
        <div className="mx-6 h-px bg-ink-900 sm:mx-10" />

        {/* Price comparison bars */}
        <div className="px-6 py-8 sm:px-10">
          {!data && !error && (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-24 h-3 animate-pulse rounded-full bg-ink-900/40" />
                  <div className="flex-1 h-3 animate-pulse rounded-full bg-ink-900/40" style={{ maxWidth: `${30 + i * 12}%` }} />
                </div>
              ))}
            </div>
          )}

          {data && countryRows.length > 0 && (
            <div className="space-y-3">
              {countryRows.map((row, i) => {
                const pct = (row.price_usd / maxPrice) * 100
                return (
                  <div key={`${row.country}-${i}`} className="group flex items-center gap-3">
                    {/* Country label */}
                    <div className="flex w-28 shrink-0 items-center gap-1.5 sm:w-36">
                      <span className="text-base leading-none" aria-hidden>
                        {FLAGS[row.country] ?? "🏳"}
                      </span>
                      <span
                        className={`truncate text-sm font-medium ${
                          row.isSelf ? "text-ink-100" : "text-ink-400"
                        }`}
                      >
                        {row.country}
                      </span>
                    </div>

                    {/* Bar */}
                    <div className="relative flex-1 h-7 overflow-hidden rounded-lg bg-ink-900/40">
                      <div
                        className={`absolute inset-y-0 left-0 rounded-lg transition-all duration-700 ${
                          row.isSelf
                            ? "bg-gradient-to-r from-amber-400 to-accent"
                            : "bg-ink-800"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                      <span
                        className={`absolute inset-y-0 left-3 flex items-center text-xs font-semibold tabular-nums ${
                          row.isSelf ? "text-zinc-900" : "text-ink-300"
                        }`}
                      >
                        ${row.price_usd.toFixed(2)}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Footer note */}
          {data && (
            <p className="mt-6 text-center text-[11px] text-ink-600">
              Prices in USD/litre · Source: CPC, Global Petrol Prices · As of {data.sri_lanka.recorded_at ? shortDate(data.sri_lanka.recorded_at) : "—"}
            </p>
          )}
        </div>

      </div>
    </section>
  )
}
