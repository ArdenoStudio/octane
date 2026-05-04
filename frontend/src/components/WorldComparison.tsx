import { useEffect, useRef, useState } from "react"
import { api, ComparisonResp, FUEL_DISPLAY, FUEL_ORDER, FuelId } from "../lib/api"
import { shortDate } from "../lib/format"

const CODES: Record<string, string> = {
  "Sri Lanka": "LK",
  India: "IN",
  Pakistan: "PK",
  Bangladesh: "BD",
  Nepal: "NP",
  Maldives: "MV",
  World: "WLD",
}

function useCountUp(target: number, duration = 650) {
  const [value, setValue] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef(0)
  const fromRef = useRef(0)

  useEffect(() => {
    fromRef.current = value
    startTimeRef.current = performance.now()
    if (timerRef.current) clearInterval(timerRef.current)

    timerRef.current = setInterval(() => {
      const t = Math.min((performance.now() - startTimeRef.current) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(fromRef.current + (target - fromRef.current) * eased)
      if (t >= 1 && timerRef.current) clearInterval(timerRef.current)
    }, 16)

    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [target, duration])

  return value
}

function AnimatedRow({
  row,
  maxPrice,
  index,
}: {
  row: { country: string; price_usd: number; isSelf: boolean }
  maxPrice: number
  index: number
}) {
  const isWorld = row.country === "World"
  const animatedPrice = useCountUp(row.price_usd, 600 + index * 40)
  const pct = (animatedPrice / maxPrice) * 100

  return (
    <div>
      {isWorld && <div className="my-3 border-t border-ink-900" />}
      <div className="flex items-center gap-3">
        <div className="w-28 shrink-0 flex items-center gap-2 sm:w-36">
          <span className={`text-[10px] font-bold tracking-widest rounded px-1.5 py-0.5 ${
            row.isSelf ? "bg-amber-100 text-amber-700" : "bg-zinc-100 text-ink-600"
          }`}>
            {CODES[row.country] ?? "??"}
          </span>
          <span className={`text-sm truncate ${row.isSelf ? "font-semibold text-ink-100" : "text-ink-400"}`}>
            {row.country}
          </span>
        </div>

        <div className="relative flex-1 h-7 overflow-hidden rounded-lg bg-ink-900/40">
          <div
            className={`absolute inset-y-0 left-0 rounded-lg ${
              row.isSelf ? "bg-gradient-to-r from-amber-400 to-accent" : "bg-ink-800"
            }`}
            style={{ width: `${pct}%` }}
          />
          <span className={`absolute inset-y-0 left-3 flex items-center text-xs font-bold tabular-nums ${
            row.isSelf ? "text-zinc-900" : "text-ink-300"
          }`}>
            ${animatedPrice.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  )
}

export function WorldComparison() {
  const [fuel, setFuel] = useState<FuelId>("petrol_95")
  const [data, setData] = useState<ComparisonResp | null>(null)
  const [error, setError] = useState<string | null>(null)
  const tabBarRef = useRef<HTMLDivElement>(null)
  const [indicator, setIndicator] = useState({ left: 0, width: 0 })

  useEffect(() => {
    setData(null)
    setError(null)
    api.worldComparison(fuel).then(setData).catch((e) => setError(String(e)))
  }, [fuel])

  useEffect(() => {
    const bar = tabBarRef.current
    if (!bar) return
    const activeBtn = bar.querySelector<HTMLButtonElement>(`[data-fuel="${fuel}"]`)
    if (!activeBtn) return
    setIndicator({ left: activeBtn.offsetLeft, width: activeBtn.offsetWidth })
  }, [fuel])

  const delta = data?.delta_vs_world_pct
  const isBelow = delta != null && delta < 0
  const direction = delta == null ? "" : delta > 0 ? "above" : delta < 0 ? "below" : "at"
  const magnitude = delta == null ? null : Math.abs(delta)

  const animatedMagnitude = useCountUp(magnitude ?? 0)

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

        <div className="h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent" />

        <div className="px-8 pt-10 pb-0 sm:px-12">
          {/* Badge */}
          <span className="inline-block rounded-full border border-amber-200/60 bg-amber-50/70 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-amber-700">
            vs the world
          </span>

          {/* Headline */}
          <div className="mt-4 flex items-baseline gap-3 flex-wrap min-h-[4rem]">
            {!data && !error && (
              <div className="h-16 w-64 animate-pulse rounded-xl bg-ink-900/40" />
            )}
            {error && (
              <p className="text-lg text-red-500">Could not load comparison data</p>
            )}
            {data && magnitude != null && (
              <>
                <span className={`text-8xl font-black tracking-tighter leading-none ${isBelow ? "text-emerald-600" : "text-red-500"}`}>
                  {animatedMagnitude.toFixed(1)}%
                </span>
                <span className="text-2xl font-bold text-ink-200 tracking-tight leading-tight">
                  {direction}<br />world average
                </span>
              </>
            )}
            {data && magnitude == null && (
              <span className="text-4xl font-extrabold tracking-tighter text-ink-200">
                Sri Lanka vs the world
              </span>
            )}
          </div>

          <p className="mt-3 text-sm text-ink-600 mb-6">
            {FUEL_DISPLAY[fuel]} · price per litre in USD
          </p>

          {/* Sliding tab indicator */}
          <div ref={tabBarRef} className="relative flex gap-0 border-b border-ink-900">
            {FUEL_ORDER.map((f) => (
              <button
                key={f}
                data-fuel={f}
                onClick={() => setFuel(f)}
                className={`px-3 py-2 text-xs font-semibold transition-colors duration-150 whitespace-nowrap ${
                  fuel === f ? "text-ink-100" : "text-ink-600 hover:text-ink-400"
                }`}
              >
                {FUEL_DISPLAY[f]}
              </button>
            ))}
            <span
              className="absolute bottom-0 h-[2px] bg-accent rounded-t-full"
              style={{
                left: indicator.left,
                width: indicator.width,
                transition: "left 250ms cubic-bezier(0.4,0,0.2,1), width 250ms cubic-bezier(0.4,0,0.2,1)",
              }}
            />
          </div>
        </div>

        {/* Bar chart */}
        <div className="px-8 py-6 sm:px-12">
          {!data && !error && (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-24 h-4 animate-pulse rounded bg-ink-900/40" />
                  <div className="flex-1 h-7 animate-pulse rounded-lg bg-ink-900/40" style={{ maxWidth: `${30 + i * 12}%` }} />
                </div>
              ))}
            </div>
          )}

          {data && countryRows.length > 0 && (
            <div className="space-y-2.5">
              {countryRows.map((row, i) => (
                <AnimatedRow key={row.country} row={row} maxPrice={maxPrice} index={i} />
              ))}
            </div>
          )}

          {data && (
            <p className="mt-6 text-[11px] text-ink-600">
              Prices in USD/litre · Source: CPC, Global Petrol Prices · As of {data.sri_lanka.recorded_at ? shortDate(data.sri_lanka.recorded_at) : "—"}
            </p>
          )}
        </div>

      </div>
    </section>
  )
}
