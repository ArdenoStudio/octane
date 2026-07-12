import { useEffect, useState } from "react";
import { RiArrowDownSLine, RiArrowUpSLine, RiFlashlightLine } from "@remixicon/react";
import { api, EarlySignal, FUEL_ORDER, FuelId, PriceChangeRow, PriceRow, resolveEarlySignals } from "../lib/api";
import { useLocale } from "../i18n/LocaleProvider";
import { lkr, relativeFromNow, shortDate } from "../lib/format";
import { Badge } from "./ui/Badge";
import { FadeContainer, FadeDiv } from "./ui/Fade";
import { ShareButtons } from "./ui/ShareButtons";

const ACCENT_BY_FUEL: Record<FuelId, string> = {
  petrol_92: "#f59e0b",
  petrol_95: "#ea580c",
  auto_diesel: "#059669",
  super_diesel: "#0891b2",
  kerosene: "#7c3aed",
};

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 72;
  const h = 24;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * (h - 6) - 3}`)
    .join(" ");
  const lx = w;
  const ly = h - ((data[data.length - 1] - min) / range) * (h - 6) - 3;
  return (
    <svg width={w} height={h} className="overflow-visible shrink-0" aria-hidden>
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.85}
      />
      <circle cx={lx} cy={ly} r="2.5" fill={color} />
    </svg>
  );
}

function DeltaText({
  delta,
  ariaLabel,
}: {
  delta: number;
  ariaLabel: string;
}) {
  const flat = delta === 0;
  const up = delta > 0;
  return (
    <span
      aria-label={ariaLabel}
      className={`inline-flex items-center gap-0.5 text-sm font-semibold tabular-nums ${
        flat ? "text-ink-500" : up ? "text-red-500" : "text-emerald-600"
      }`}
    >
      {!flat && (up ? <RiArrowUpSLine className="size-4" /> : <RiArrowDownSLine className="size-4" />)}
      {flat ? "0" : up ? `+${Math.round(delta)}` : `${Math.round(delta)}`}
    </span>
  );
}

export function PriceStrip() {
  const { m, fuelLabel } = useLocale();
  const [rows, setRows] = useState<PriceRow[] | null>(null);
  const [changes, setChanges] = useState<PriceChangeRow[] | null>(null);
  const [lastVerifiedAt, setLastVerifiedAt] = useState<string | null>(null);
  const [earlySignals, setEarlySignals] = useState<EarlySignal[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.latest(), api.changes(40)])
      .then(([latest, changesResp]) => {
        setRows(latest.prices);
        setChanges(changesResp.changes);
        setLastVerifiedAt(latest.last_verified_at ?? null);
        setEarlySignals(resolveEarlySignals(latest));
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

  const signalByFuel: Partial<Record<FuelId, EarlySignal>> = {};
  for (const s of earlySignals) {
    // Prefer news over LIOC when both exist for the same fuel.
    const existing = signalByFuel[s.fuel_type];
    if (!existing || (existing.source !== "news" && s.source === "news")) {
      signalByFuel[s.fuel_type] = s;
    }
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
      return row ? `${fuelLabel(f)}: LKR ${row.price_lkr}` : null;
    }).filter(Boolean);
    return `Sri Lanka fuel prices today:\n${lines.join(" · ")}\n\nTrack prices, set alerts, and calculate trip costs at`;
  }

  return (
    <section id="prices" className="container-x pt-10 sm:pt-14">
      <FadeContainer>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <FadeDiv>
            <Badge>{m.prices.badge}</Badge>
            <h1 className="mt-3 font-display text-3xl font-bold tracking-tightest text-ink-100 sm:text-4xl">
              {m.prices.title}
            </h1>
          </FadeDiv>
          {(lastRevision || lastVerifiedAt) && (
            <FadeDiv className="text-sm text-ink-400 sm:text-right">
              {lastRevision && (
                <div>
                  {m.prices.lastRevision}{" "}
                  <span className="font-medium text-ink-200">{shortDate(lastRevision)}</span>
                  <span className="ml-1 text-ink-500">· {relativeFromNow(lastRevision)}</span>
                </div>
              )}
              {lastVerifiedAt && (
                <div className={lastRevision ? "mt-0.5 text-xs text-ink-500" : undefined}>
                  {m.prices.lastChecked}{" "}
                  <span className="text-ink-300">{relativeFromNow(lastVerifiedAt)}</span>
                </div>
              )}
            </FadeDiv>
          )}
        </div>

        {/* Today's revision notice */}
        {todayRevisions.length > 0 && (
          <FadeDiv className="mt-6">
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-y border-emerald-600/15 bg-emerald-50/40 px-1 py-3 sm:px-2">
              <span className="flex items-center gap-1.5 text-sm font-semibold text-emerald-700">
                <RiFlashlightLine className="size-4" />
                {m.prices.revisedToday}
              </span>
              <span className="flex flex-wrap gap-x-4 gap-y-1">
                {FUEL_ORDER.map((fuel) => {
                  const c = todayRevisions.find((r) => r.fuel_type === fuel);
                  const row = cpcByFuel[fuel];
                  if (!c && !row) return null;
                  if (!c) {
                    return (
                      <span key={fuel} className="flex items-center gap-1 text-sm text-ink-500">
                        <span>{fuelLabel(fuel)}</span>
                        <span>unchanged · {lkr(row!.price_lkr, { showSymbol: false })}</span>
                      </span>
                    );
                  }
                  const up = (c.delta_lkr ?? 0) > 0;
                  return (
                    <span key={fuel} className="flex items-center gap-1 text-sm text-ink-300">
                      <span className="text-ink-500">{fuelLabel(fuel)}</span>
                      {up ? (
                        <RiArrowUpSLine className="size-4 text-red-500" />
                      ) : (
                        <RiArrowDownSLine className="size-4 text-emerald-600" />
                      )}
                      <span className={up ? "font-semibold text-red-500" : "font-semibold text-emerald-600"}>
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

        {/* Early signals — single notice, not repeated in every column */}
        {earlySignals.length > 0 && todayRevisions.length === 0 && (
          <FadeDiv className="mt-6">
            <div className="border-y border-ink-800 bg-ink-900/50 px-1 py-3 sm:px-2">
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
                <span className="inline-flex items-center gap-1.5 font-semibold text-ink-200">
                  <RiFlashlightLine className="size-4 text-accent" />
                  {m.prices.earlySignalTitle}
                </span>
                <span className="text-ink-500">{m.prices.earlySignalUnconfirmed}</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1.5">
                {earlySignals.map((s) => {
                  const up = s.delta_lkr > 0;
                  const sourceLabel =
                    s.source === "news" ? m.prices.earlySignalNews : m.prices.earlySignalLioc;
                  return (
                    <span
                      key={`${s.source}-${s.fuel_type}`}
                      className="flex items-center gap-1.5 text-sm text-ink-300"
                    >
                      <span className="text-ink-500">{sourceLabel}</span>
                      <span>{fuelLabel(s.fuel_type)}</span>
                      <span className="font-semibold tabular-nums text-ink-100">
                        {lkr(s.price_lkr, { showSymbol: false })}
                      </span>
                      <span className={up ? "tabular-nums text-red-500" : "tabular-nums text-emerald-600"}>
                        ({up ? "+" : ""}
                        {lkr(s.delta_lkr, { showSymbol: false })})
                      </span>
                    </span>
                  );
                })}
              </div>
            </div>
          </FadeDiv>
        )}

        {error && (
          <FadeDiv className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            {m.prices.loadError}{" "}
            <span className="text-red-400">{error}</span>
          </FadeDiv>
        )}

        {/* Unified price board — equal columns, no stacked card chrome */}
        <div className="price-board mt-6 overflow-hidden rounded-2xl border border-ink-800 bg-white/80 shadow-[0_1px_2px_rgba(24,24,27,0.04)] backdrop-blur-[2px]">
          <div className="grid grid-cols-1 divide-y divide-ink-800 sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-5">
            {FUEL_ORDER.map((fuel, index) => {
              const row = cpcByFuel[fuel];
              const history = historyByFuel[fuel];
              const delta = deltaByFuel[fuel];
              const hasDelta = delta !== undefined && delta !== null;
              const up = hasDelta && delta! > 0;
              const flat = hasDelta && delta === 0;
              const signal = signalByFuel[fuel];
              const signalUp = signal ? signal.delta_lkr > 0 : false;
              const accent = ACCENT_BY_FUEL[fuel];

              return (
                <FadeDiv
                  key={fuel}
                  className={`price-board-col relative flex min-h-[11.5rem] flex-col p-5 sm:p-6 ${
                    index > 0 ? "lg:border-l lg:border-ink-800" : ""
                  } ${index % 2 === 1 ? "sm:border-l sm:border-ink-800 lg:border-l" : ""} ${
                    index >= 2 ? "sm:border-t sm:border-ink-800 lg:border-t-0" : ""
                  }`}
                >
                  <div
                    aria-hidden
                    className="price-board-accent absolute inset-x-0 top-0 h-[2px]"
                    style={{ backgroundColor: accent }}
                  />

                  <div className="flex items-start justify-between gap-2">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-400">
                      {fuelLabel(fuel)}
                    </div>
                    {hasDelta && (
                      <DeltaText
                        delta={delta!}
                        ariaLabel={
                          flat
                            ? "no change"
                            : up
                              ? `price up ${Math.round(delta!)} rupees`
                              : `price down ${Math.abs(Math.round(delta!))} rupees`
                        }
                      />
                    )}
                  </div>

                  <div className="mt-3 flex items-baseline gap-1.5">
                    <div className="font-display text-[2.35rem] font-bold leading-none tracking-tightest text-ink-100 tabular-nums">
                      {row ? lkr(row.price_lkr, { showSymbol: false }) : "—"}
                    </div>
                  </div>

                  <div className="mt-2 text-xs text-ink-500">
                    {row ? `${m.prices.lkrPer} ${shortDate(row.recorded_at)}` : m.prices.awaitingData}
                  </div>

                  {/* Reserved signal slot keeps columns aligned */}
                  <div className="mt-4 min-h-[2.75rem]">
                    {signal ? (
                      <div className="text-xs leading-relaxed text-ink-500">
                        <span className="font-medium text-ink-400">
                          {m.prices.unconfirmed}
                          <span className="font-normal text-ink-500">
                            {" "}
                            · {signal.source === "news" ? m.prices.earlySignalNews : m.prices.earlySignalLioc}
                          </span>
                        </span>
                        <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
                          <span className="font-display text-base font-semibold tabular-nums text-ink-200">
                            {lkr(signal.price_lkr, { showSymbol: false })}
                          </span>
                          <span
                            className={`tabular-nums ${
                              signalUp ? "text-red-500" : "text-emerald-600"
                            }`}
                          >
                            {signalUp ? "+" : ""}
                            {lkr(signal.delta_lkr, { showSymbol: false })}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs text-ink-600/70">{m.prices.official} · CPC</div>
                    )}
                  </div>

                  <div className="mt-auto flex items-end justify-end pt-3">
                    {history && row ? (
                      <Sparkline data={history} color={accent} />
                    ) : (
                      <div className="h-6" />
                    )}
                  </div>
                </FadeDiv>
              );
            })}
          </div>
        </div>

        {rows && (
          <FadeDiv className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-ink-400">
              {m.prices.footerSource}{" "}
              <a
                href="https://ceypetco.gov.lk"
                target="_blank"
                rel="noopener noreferrer"
                className="text-ink-300 underline-offset-2 hover:underline"
              >
                Ceylon Petroleum Corporation
              </a>
              {m.prices.footerLegal}
            </p>
            <ShareButtons text={buildShareMessage()} />
          </FadeDiv>
        )}
      </FadeContainer>
    </section>
  );
}
