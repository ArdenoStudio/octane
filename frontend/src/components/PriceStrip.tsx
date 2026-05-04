import { useEffect, useState } from "react";
import { RiArrowDownSLine, RiArrowUpSLine, RiFlashlightLine } from "@remixicon/react";
import { api, FUEL_DISPLAY, FUEL_ORDER, FuelId, PriceChangeRow, PriceRow } from "../lib/api";
import { lkr, relativeFromNow, shortDate } from "../lib/format";
import { Badge } from "./ui/Badge";
import { BadgeDelta } from "./ui/BadgeDelta";
import { FadeContainer, FadeDiv } from "./ui/Fade";
import { ShareButtons } from "./ui/ShareButtons";

const GRADIENT_BY_FUEL: Record<FuelId, string> = {
  petrol_92:    "from-amber-500/20",
  petrol_95:    "from-orange-500/20",
  auto_diesel:  "from-emerald-500/15",
  super_diesel: "from-cyan-500/15",
  kerosene:     "from-violet-500/15",
};

const SPARK_COLOR: Record<FuelId, string> = {
  petrol_92:    "#f59e0b",
  petrol_95:    "#f97316",
  auto_diesel:  "#10b981",
  super_diesel: "#06b6d4",
  kerosene:     "#8b5cf6",
};

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 80;
  const h = 28;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * (h - 6) - 3}`)
    .join(" ");
  const lx = w;
  const ly = h - ((data[data.length - 1] - min) / range) * (h - 6) - 3;
  return (
    <svg width={w} height={h} className="overflow-visible shrink-0">
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={lx} cy={ly} r="3" fill={color} />
    </svg>
  );
}

export function PriceStrip() {
  const [rows, setRows] = useState<PriceRow[] | null>(null);
  const [changes, setChanges] = useState<PriceChangeRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.latest(), api.changes(40)])
      .then(([latest, changesResp]) => {
        setRows(latest.prices);
        setChanges(changesResp.changes);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const cpcByFuel: Partial<Record<FuelId, PriceRow>> = {};
  rows?.forEach((r) => {
    if (r.source === "cpc") cpcByFuel[r.fuel_type] = r;
  });

  const historyByFuel: Partial<Record<FuelId, number[]>> = {};
  const deltaByFuel: Partial<Record<FuelId, number | null>> = {};
  if (changes) {
    FUEL_ORDER.forEach((fuel) => {
      const sorted = [...changes.filter((c) => c.fuel_type === fuel)].sort((a, b) =>
        a.recorded_at.localeCompare(b.recorded_at),
      );
      const pts = sorted.slice(-8).map((c) => c.price_lkr);
      if (pts.length > 1) historyByFuel[fuel] = pts;
      const last = sorted[sorted.length - 1];
      deltaByFuel[fuel] = last?.delta_lkr ?? null;
    });
  }

  const todayStr = new Date().toISOString().slice(0, 10);

  const lastRevision = rows
    ? rows
        .filter((r) => r.source === "cpc")
        .map((r) => r.recorded_at)
        .sort()
        .pop()
    : null;

  // Fuel types with an actual price change recorded today
  const todayRevisions =
    changes?.filter((c) => c.recorded_at === todayStr && c.delta_lkr !== null && c.delta_lkr !== 0) ?? [];

  function buildShareMessage(): string {
    const lines = FUEL_ORDER.map((f) => {
      const row = cpcByFuel[f];
      return row ? `${FUEL_DISPLAY[f]}: LKR ${row.price_lkr}` : null;
    }).filter(Boolean);
    return `🇱🇰 Sri Lanka fuel prices today:\n${lines.join(" · ")}\n\nTrack prices, set alerts & calculate trip costs 👇`;
  }

  return (
    <section id="prices" className="container-x pt-10 sm:pt-14">
      <FadeContainer>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <FadeDiv>
            <Badge>Live prices · CPC</Badge>
            <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tightest sm:text-4xl">
              Sri Lanka fuel prices, today.
            </h1>
          </FadeDiv>
          {lastRevision && (
            <FadeDiv className="text-right text-sm text-ink-400">
              Last revision{" "}
              <span className="text-ink-200">{shortDate(lastRevision)}</span>
              <span className="ml-1 text-ink-400">· {relativeFromNow(lastRevision)}</span>
            </FadeDiv>
          )}
        </div>

        {/* Today's revision notice — only shown when prices were actually revised today */}
        {todayRevisions.length > 0 && (
          <FadeDiv className="mt-5">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
              <span className="flex items-center gap-1.5 text-sm font-semibold text-emerald-400">
                <RiFlashlightLine className="size-4" />
                Prices revised today
              </span>
              <span className="flex flex-wrap gap-x-4 gap-y-1">
                {todayRevisions.map((c) => {
                  const up = (c.delta_lkr ?? 0) > 0;
                  return (
                    <span key={c.fuel_type} className="flex items-center gap-1 text-sm text-ink-300">
                      <span className="text-ink-500">{FUEL_DISPLAY[c.fuel_type as FuelId]}</span>
                      {up ? (
                        <RiArrowUpSLine className="size-4 text-red-400" />
                      ) : (
                        <RiArrowDownSLine className="size-4 text-emerald-400" />
                      )}
                      <span className={up ? "font-semibold text-red-400" : "font-semibold text-emerald-400"}>
                        {up ? "+" : ""}
                        {lkr(c.delta_lkr ?? 0, { showSymbol: false })}
                      </span>
                      <span className="text-ink-500">→ {lkr(c.price_lkr, { showSymbol: false })}</span>
                    </span>
                  );
                })}
              </span>
            </div>
          </FadeDiv>
        )}

        {error && (
          <FadeDiv className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            Couldn't load prices. The API may be offline.{" "}
            <span className="text-red-400">{error}</span>
          </FadeDiv>
        )}

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {FUEL_ORDER.map((fuel) => {
            const row = cpcByFuel[fuel];
            const history = historyByFuel[fuel];
            const delta = deltaByFuel[fuel];
            const hasDelta = delta !== undefined && delta !== null;
            const up = hasDelta && delta! > 0;
            const flat = hasDelta && delta === 0;
            return (
              <FadeDiv key={fuel}>
                <div className="card relative overflow-hidden p-6 h-full flex flex-col gap-3 hover:shadow-md transition-shadow">
                  {/* Soft per-fuel gradient bleed */}
                  <div
                    aria-hidden
                    className={`pointer-events-none absolute -inset-x-4 -top-10 h-24 bg-gradient-to-b ${GRADIENT_BY_FUEL[fuel]} to-transparent blur-3xl opacity-50`}
                  />

                  <div className="relative flex flex-col gap-3">
                    {/* Label + delta badge */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="label">{FUEL_DISPLAY[fuel]}</div>
                      {hasDelta && (
                        <BadgeDelta
                          aria-label={flat ? "no change" : up ? `price up ${Math.round(delta!)} rupees` : `price down ${Math.abs(Math.round(delta!))} rupees`}
                          variant="solid"
                          deltaType={flat ? "neutral" : up ? "decrease" : "increase"}
                          value={flat ? "0" : up ? `+${Math.round(delta!)}` : `${Math.round(delta!)}`}
                          className="shrink-0 tabular-nums"
                        />
                      )}
                    </div>

                    {/* Price */}
                    <div className="font-mono text-4xl font-black tracking-tight text-ink-100 tabular-nums leading-none">
                      {row ? lkr(row.price_lkr, { showSymbol: false }) : "—"}
                    </div>

                    {/* Date + sparkline */}
                    <div className="flex items-end justify-between">
                      <div className="text-xs text-ink-400">
                        {row ? `LKR · ${shortDate(row.recorded_at)}` : "Awaiting data"}
                      </div>
                      {history && row && (
                        <Sparkline data={history} color={SPARK_COLOR[fuel]} />
                      )}
                    </div>
                  </div>
                </div>
              </FadeDiv>
            );
          })}
        </div>

        {rows && (
          <FadeDiv className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-ink-400">
              Source:{" "}
              <a
                href="https://ceypetco.gov.lk"
                target="_blank"
                rel="noopener noreferrer"
                className="text-ink-300 underline-offset-2 hover:underline"
              >
                Ceylon Petroleum Corporation
              </a>
              {" · "}Scraped daily at 8 AM · Independent, not affiliated.
            </p>
            <ShareButtons text={buildShareMessage()} />
          </FadeDiv>
        )}
      </FadeContainer>
    </section>
  );
}
