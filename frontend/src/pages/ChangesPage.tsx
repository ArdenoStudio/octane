import { useEffect, useState } from "react";
import { RiArrowDownLine, RiArrowUpLine } from "@remixicon/react";
import { api, FUEL_DISPLAY, FuelId, PriceChangeRow } from "../lib/api";
import { lkr, shortDate } from "../lib/format";
import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";
import { Badge } from "../components/ui/Badge";
import { FadeContainer, FadeDiv } from "../components/ui/Fade";

const FUEL_ACCENT: Record<FuelId, string> = {
  petrol_92: "text-amber-600 bg-amber-50 border-amber-200",
  petrol_95: "text-orange-600 bg-orange-50 border-orange-200",
  auto_diesel: "text-emerald-600 bg-emerald-50 border-emerald-200",
  super_diesel: "text-cyan-600 bg-cyan-50 border-cyan-200",
  kerosene: "text-violet-600 bg-violet-50 border-violet-200",
};

function groupByDate(rows: PriceChangeRow[]): [string, PriceChangeRow[]][] {
  const map = new Map<string, PriceChangeRow[]>();
  for (const r of rows) {
    const key = r.recorded_at.slice(0, 10);
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(r);
  }
  return [...map.entries()];
}

export function ChangesPage() {
  const [rows, setRows] = useState<PriceChangeRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Price Changes — Octane";
    return () => { document.title = "Octane — Live Sri Lanka Fuel Prices"; };
  }, []);

  useEffect(() => {
    api
      .changes()
      .then((r) => setRows(r.changes))
      .catch((e) => setError(String(e)));
  }, []);

  const groups = rows ? groupByDate(rows) : [];

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="container-x py-10 sm:py-14">
        <FadeContainer>
          <FadeDiv>
            <Badge>Price revisions · CPC</Badge>
            <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tightest text-ink-100 sm:text-4xl">
              Every price change on record.
            </h1>
            <p className="mt-3 text-ink-300">
              A full audit trail of CPC fuel price revisions — date, new price,
              and the delta vs the prior revision.
            </p>
            <a
              href="/"
              className="mt-4 inline-block text-sm text-ink-400 hover:text-ink-200 transition-colors"
            >
              ← Back to live prices
            </a>
          </FadeDiv>

          {error && (
            <FadeDiv className="mt-8 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
              Couldn't load changes. The API may be offline.{" "}
              <span className="text-red-400">{error}</span>
            </FadeDiv>
          )}

          {rows && rows.length === 0 && (
            <FadeDiv className="mt-8 text-ink-400">No revisions on record yet.</FadeDiv>
          )}

          {groups.length > 0 && (
            <div className="mt-10 space-y-8">
              {groups.map(([date, revisions]) => (
                <FadeDiv key={date}>
                  <div className="mb-3 text-sm font-semibold text-ink-300">
                    {shortDate(date + "T00:00:00")}
                  </div>
                  <div className="card divide-y divide-ink-800 overflow-hidden p-0">
                    {revisions.map((r, i) => {
                      const isFirst = r.previous_lkr === null;
                      const up = (r.delta_lkr ?? 0) > 0;
                      const down = (r.delta_lkr ?? 0) < 0;
                      return (
                        <div
                          key={i}
                          className="flex items-center justify-between gap-4 px-5 py-4"
                        >
                          <div className="flex items-center gap-3">
                            <span
                              className={`inline-flex rounded-md border px-2 py-0.5 text-xs font-medium ${FUEL_ACCENT[r.fuel_type as FuelId]}`}
                            >
                              {FUEL_DISPLAY[r.fuel_type as FuelId]}
                            </span>
                            <span className="font-display text-lg font-extrabold tracking-tightest text-ink-100">
                              {lkr(r.price_lkr, { showSymbol: false })}
                              <span className="ml-1 text-xs font-normal text-ink-400">
                                LKR
                              </span>
                            </span>
                          </div>
                          <div className="text-right text-sm">
                            {isFirst ? (
                              <span className="text-ink-400">First record</span>
                            ) : r.delta_lkr !== null ? (
                              <span
                                className={`flex items-center gap-1 font-semibold ${up ? "text-red-600" : down ? "text-emerald-600" : "text-ink-400"}`}
                              >
                                {up && <RiArrowUpLine className="size-4" />}
                                {down && <RiArrowDownLine className="size-4" />}
                                {up ? "+" : ""}
                                {r.delta_lkr.toFixed(2)}
                                {r.delta_pct !== null && (
                                  <span className="ml-1 text-xs font-normal text-ink-400">
                                    ({r.delta_pct > 0 ? "+" : ""}
                                    {r.delta_pct.toFixed(1)}%)
                                  </span>
                                )}
                              </span>
                            ) : (
                              <span className="text-ink-400">—</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </FadeDiv>
              ))}
            </div>
          )}

          {!rows && !error && (
            <div className="mt-10 space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="card h-16 animate-pulse" />
              ))}
            </div>
          )}
        </FadeContainer>
      </main>
      <Footer />
    </div>
  );
}
