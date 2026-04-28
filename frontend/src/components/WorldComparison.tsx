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
      width: 900 * 2,
      height: 900 * 2,
      phi,
      theta: 0.15,
      dark: 1,
      diffuse: 1.5,
      mapSamples: 25000,
      mapBrightness: 14,
      mapBaseBrightness: 0.06,
      baseColor: [0.3, 0.3, 0.3],
      glowColor: [0.6, 0.38, 0.08],
      markerColor: [0.98, 0.62, 0.04],
      markers: MARKERS,
      onRender: (state: Record<string, unknown>) => {
        state.phi = phi
        phi += 0.003
      },
    } as Parameters<typeof createGlobe>[1])

    return () => globe.destroy()
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-0"
      style={{ width: 900, height: 900 }}
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
      <div className="relative overflow-hidden rounded-3xl bg-gray-950 pt-24 shadow-xl shadow-black/30 md:pt-28">
        {/* Amber glow blob */}
        <div className="absolute top-[17rem] left-1/2 -translate-x-1/2 size-[40rem] rounded-full bg-amber-700/30 blur-3xl md:top-[20rem]" />

        {/* Top content */}
        <div className="relative z-10 flex flex-col items-center px-6 text-center">
          {/* Badge */}
          <div className="inline-block rounded-lg border border-accent/20 bg-accent/10 px-3 py-1.5 text-sm font-semibold uppercase leading-4 tracking-tight">
            <span className="bg-gradient-to-b from-amber-200 to-accent bg-clip-text text-transparent">
              vs the world
            </span>
          </div>

          {/* Dynamic headline */}
          <h2 className="mt-6 inline-block bg-gradient-to-b from-white to-amber-100 bg-clip-text px-2 text-center text-5xl font-bold tracking-tighter text-transparent md:text-7xl">
            {error || !data ? (
              <>Sri Lanka<br />vs the world</>
            ) : magnitude == null ? (
              "World data unavailable"
            ) : (
              <>
                {magnitude.toFixed(1)}%{" "}
                {direction}
                <br />
                world average
              </>
            )}
          </h2>

          <p className="mt-3 text-sm text-amber-200/40">
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
                    : "border border-white/10 text-white/30 hover:border-white/20 hover:text-white/60"
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
        <div className="z-20 -mt-32 h-[36rem] w-full overflow-hidden md:-mt-36">
          <div className="absolute bottom-0 h-3/5 w-full bg-gradient-to-b from-transparent via-gray-950/95 to-gray-950" />

          <div className="absolute inset-x-4 bottom-8 m-auto max-w-5xl md:top-2/3 md:inset-x-6 md:bottom-10">
            {!data && !error && (
              <p className="text-center text-sm text-white/20">Loading comparison…</p>
            )}
            {error && (
              <p className="text-center text-sm text-red-400">{error}</p>
            )}
            {data && countryRows.length > 0 && (
              <div className="flex flex-wrap justify-between gap-x-2 gap-y-6 rounded-xl border border-white/[3%] bg-white/[2%] p-4 shadow-xl backdrop-blur md:p-6">
                {countryRows.map((row, i) => (
                  <div key={`${row.country}-${i}`} className="flex min-w-[70px] flex-1 flex-col gap-1">
                    <div className="flex items-center gap-1.5 text-xs text-amber-200/40">
                      <span aria-hidden>{FLAGS[row.country] ?? "🏳"}</span>
                      <span className="truncate">{row.country}</span>
                    </div>
                    <div className="font-mono text-base font-semibold text-white/80">
                      ${row.price_usd?.toFixed(2)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-white/20">
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
