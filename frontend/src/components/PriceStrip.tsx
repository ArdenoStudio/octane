import { useEffect, useState } from "react";
import { api, FUEL_DISPLAY, FUEL_ORDER, FuelId, PriceRow } from "../lib/api";
import { lkr, relativeFromNow, shortDate } from "../lib/format";
import { Badge } from "./ui/Badge";
import { FadeContainer, FadeDiv } from "./ui/Fade";
import { ShareButtons } from "./ui/ShareButtons";

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

        {error && (
          <FadeDiv className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            Couldn't load prices. The API may be offline.{" "}
            <span className="text-red-400">{error}</span>
          </FadeDiv>
        )}

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {FUEL_ORDER.map((fuel) => {
            const row = cpcByFuel[fuel];
            return (
              <FadeDiv key={fuel}>
                <div className="card relative overflow-hidden p-5 h-full">
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
