import createGlobe from "cobe"
import { useEffect, useRef, useState } from "react"
import { api, ComparisonResp, FUEL_DISPLAY, FUEL_ORDER, FuelId } from "../lib/api"

const FLAGS: Record<string, string> = {
  "Sri Lanka": "🇱🇰",
  India: "🇮🇳",
  Pakistan: "🇵🇰",
  Bangladesh: "🇧🇩",
  Nepal: "🇳🇵",
  Maldives: "🇲🇻",
  World: "🌐",
}

// South Asian region coordinates for globe markers
const MARKERS = [
  { location: [7.8731, 80.7718] as [number, number], size: 0.06 },   // Sri Lanka
  { location: [20.5937, 78.9629] as [number, number], size: 0.04 },  // India
  { location: [23.685, 90.3563] as [number, number], size: 0.03 },   // Bangladesh
  { location: [28.3949, 84.124] as [number, number], size: 0.03 },   // Nepal
  { location: [30.3753, 69.3451] as [number, number], size: 0.03 },  // Pakistan
  { location: [3.2028, 73.2207] as [number, number], size: 0.03 },   // Maldives
]

function GlobeCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    let phi = 1.2

    const globe = createGlobe(canvasRef.current!, {
      devicePixelRatio: 2,
      width: 1200 * 2,
      height: 1200 * 2,
      phi,
      theta: -0.25,
      dark: 0,
      diffuse: 0.8,
      mapSamples: 25000,
      mapBrightness: 6,
      mapBaseBrightness: 0.1,
      baseColor: [0.9, 0.88, 0.84],
      glowColor: [0.97, 0.88, 0.7],
      markerColor: [0.98, 0.62, 0.04],
      markers: MARKERS,
      onRender: (state: Record<string, unknown>) => {
        state.phi = phi
        phi += 0.0002
      },
    } as Parameters<typeof createGlobe>[1])

    return () => globe.destroy()
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute top-[7rem] z-20 aspect-square size-full max-w-fit md:top-[11rem]"
      style={{ width: 1200, height: 1200 }}
    />
  )
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
  const direction =
    delta == null ? "" : delta > 0 ? "above" : delta < 0 ? "below" : "in line with"
  const magnitude = delta == null ? null : Math.abs(delta)

  const countryRows = data
    ? [
        { country: "Sri Lanka", price_usd: data.sri_lanka.price_usd ?? 0 },
        ...data.neighbors,
        data.world_average_usd != null
          ? { country: "World", price_usd: data.world_average_usd }
          : null,
      ].filter(Boolean) as { country: string; price_usd: number }[]
    : []

  return (
    <section id="world" className="container-x pt-16">
      <div className="relative overflow-hidden rounded-3xl border border-ink-800 bg-ink-900 pt-20 shadow-sm md:pt-24">
        {/* Amber glow blob */}
        <div className="absolute top-64 left-1/2 -translate-x-1/2 size-96 rounded-full bg-amber-400/10 blur-3xl md:top-72" />

        {/* Top content */}
        <div className="relative z-10 flex flex-col items-center px-6 text-center">
          {/* Badge */}
          <div className="inline-block rounded-lg border border-accent/20 bg-accent/10 px-3 py-1.5 text-sm font-semibold uppercase leading-4 tracking-tight text-accent-dark">
            vs the world
          </div>

          {/* Dynamic headline */}
          <h2 className="mt-5 max-w-2xl px-2 text-4xl font-bold tracking-tighter text-ink-100 sm:text-5xl md:text-6xl">
            {error || !data ? (
              "Sri Lanka vs the world"
            ) : magnitude == null ? (
              "World data unavailable"
            ) : (
              <>
                {magnitude.toFixed(1)}%{" "}
                <span className="text-accent">{direction}</span>{" "}
                world average
              </>
            )}
          </h2>

          <p className="mt-3 text-sm text-ink-400">
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
                    ? "bg-accent text-zinc-900"
                    : "border border-ink-700 text-ink-400 hover:border-ink-600 hover:text-ink-200"
                }`}
              >
                {FUEL_DISPLAY[f]}
              </button>
            ))}
          </div>
        </div>

        {/* Globe */}
        <GlobeCanvas />

        {/* Bottom fade + cards */}
        <div className="z-20 -mt-28 h-[34rem] w-full overflow-hidden md:-mt-32">
          <div className="absolute bottom-0 h-3/5 w-full bg-gradient-to-b from-transparent via-ink-900/95 to-ink-900" />

          <div className="absolute inset-x-4 bottom-8 m-auto max-w-5xl md:top-2/3 md:inset-x-6 md:bottom-10">
            {!data && !error && (
              <p className="text-center text-sm text-ink-600">Loading comparison…</p>
            )}
            {error && (
              <p className="text-center text-sm text-red-500">{error}</p>
            )}
            {data && countryRows.length > 0 && (
              <div className="grid grid-cols-2 gap-3 rounded-xl border border-ink-800 bg-white/60 p-4 shadow-sm backdrop-blur-sm sm:grid-cols-4 md:p-6 lg:grid-cols-7">
                {countryRows.map((row, i) => (
                  <div key={`${row.country}-${i}`} className="flex flex-col gap-1">
                    <div className="flex items-center gap-1.5 text-xs text-ink-400">
                      <span aria-hidden>{FLAGS[row.country] ?? "🏳"}</span>
                      <span className="truncate">{row.country}</span>
                    </div>
                    <div className="font-mono text-base font-semibold text-ink-100">
                      ${row.price_usd?.toFixed(2)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-ink-600">
                      USD / L
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
