import { useEffect, useState } from "react";
import {
  RiArrowDownLine,
  RiArrowRightLine,
  RiArrowUpLine,
  RiGlobalLine,
  RiLineChartLine,
  RiMoneyDollarCircleLine,
} from "@remixicon/react";
import { api, MarketContextResp } from "../lib/api";
import { relativeFromNow } from "../lib/format";
import { FadeContainer, FadeDiv } from "./ui/Fade";
import { Badge } from "./ui/Badge";

function DirectionIcon({ direction }: { direction: "up" | "down" | "stable" }) {
  if (direction === "up") return <RiArrowUpLine className="size-4 text-red-400" />;
  if (direction === "down") return <RiArrowDownLine className="size-4 text-emerald-400" />;
  return <RiArrowRightLine className="size-4 text-ink-400" />;
}

export function MarketContextStrip() {
  const [data, setData] = useState<MarketContextResp | null>(null);

  useEffect(() => {
    api.marketContext()
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) return null;
  if (!data.sentiment && !data.fx && !data.world) return null;

  const sentiment = data.sentiment;
  const mag = sentiment ? Math.abs(Math.round(sentiment.magnitude_lkr)) : 0;
  const magLabel =
    sentiment && mag > 0
      ? `${sentiment.direction === "up" ? "+" : sentiment.direction === "down" ? "−" : ""}${mag} LKR`
      : null;

  return (
    <section id="market-context" className="container-x pt-6 sm:pt-8" aria-label="Daily market context">
      <FadeContainer>
        <FadeDiv>
          <Badge>Daily context</Badge>
          <h2 className="mt-3 font-display text-xl font-bold tracking-tightest sm:text-2xl">
            Between CPC revisions
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-400">
            Official pump prices only change when CPC revises. These signals update more often so
            you can see market pressure in between.
          </p>
        </FadeDiv>

        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {sentiment && (
            <FadeDiv>
              <div className="rounded-xl border border-ink-800 bg-ink-900/40 p-4 h-full">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
                  <RiLineChartLine className="size-3.5" />
                  Revision outlook
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <DirectionIcon direction={sentiment.direction} />
                  <span className="font-display text-lg font-bold text-ink-100 capitalize">
                    {sentiment.direction === "stable" ? "Stable" : sentiment.direction}
                  </span>
                  {magLabel && (
                    <span className="text-sm tabular-nums text-ink-300">{magLabel}</span>
                  )}
                </div>
                <p className="mt-2 text-sm text-ink-400 line-clamp-3">{sentiment.summary}</p>
                <p className="mt-2 text-xs text-ink-500">
                  AI · {Math.round(sentiment.confidence * 100)}% confidence
                  {sentiment.generated_at
                    ? ` · ${relativeFromNow(sentiment.generated_at)}`
                    : null}
                </p>
              </div>
            </FadeDiv>
          )}

          {data.fx && (
            <FadeDiv>
              <div className="rounded-xl border border-ink-800 bg-ink-900/40 p-4 h-full">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
                  <RiMoneyDollarCircleLine className="size-3.5" />
                  USD / LKR
                </div>
                <div className="mt-3 font-mono text-2xl font-black tabular-nums text-ink-100">
                  {data.fx.usd_lkr.toFixed(2)}
                </div>
                <p className="mt-2 text-sm text-ink-400">
                  Exchange rate used for world comparisons.
                </p>
                <p className="mt-2 text-xs text-ink-500">
                  As of {data.fx.recorded_at}
                </p>
              </div>
            </FadeDiv>
          )}

          {data.world && data.world.world_average_usd != null && (
            <FadeDiv>
              <div className="rounded-xl border border-ink-800 bg-ink-900/40 p-4 h-full">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
                  <RiGlobalLine className="size-3.5" />
                  vs world average
                </div>
                <div className="mt-3 font-mono text-2xl font-black tabular-nums text-ink-100">
                  {data.world.delta_vs_world_pct == null
                    ? "—"
                    : `${data.world.delta_vs_world_pct > 0 ? "+" : ""}${data.world.delta_vs_world_pct.toFixed(1)}%`}
                </div>
                <p className="mt-2 text-sm text-ink-400">
                  Sri Lanka vs global average (petrol 95 · USD/L).
                </p>
                <p className="mt-2 text-xs text-ink-500">
                  World avg ${data.world.world_average_usd.toFixed(2)}/L
                </p>
              </div>
            </FadeDiv>
          )}
        </div>
      </FadeContainer>
    </section>
  );
}
