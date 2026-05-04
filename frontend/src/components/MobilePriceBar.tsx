import { useEffect, useState } from "react";
import { RiBellLine, RiWhatsappLine } from "@remixicon/react";
import { api, PriceRow } from "../lib/api";
import { lkr } from "../lib/format";

export function MobilePriceBar() {
  const [price92, setPrice92] = useState<PriceRow | null>(null);

  useEffect(() => {
    api
      .latest()
      .then((r) => {
        const row = r.prices.find(
          (p) => p.fuel_type === "petrol_92" && p.source === "cpc",
        );
        if (row) setPrice92(row);
      })
      .catch(() => {});
  }, []);

  if (!price92) return null;

  const waText = encodeURIComponent(
    `🇱🇰 Petrol 92 in Sri Lanka: LKR ${price92.price_lkr} today.\n\nTrack all fuel prices, set alerts & calculate trip costs at octane.lk`,
  );

  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 flex items-center justify-between gap-3 border-t border-ink-800 bg-white/95 px-4 py-3 backdrop-blur-sm sm:hidden">
      <div>
        <div className="text-xs text-ink-400">Petrol 92 · CPC</div>
        <div className="font-display text-xl font-extrabold tracking-tightest text-ink-100">
          {lkr(price92.price_lkr, { showSymbol: false })}
          <span className="ml-1 text-xs font-normal text-ink-400">LKR</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <a
          href={`https://wa.me/?text=${waText}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 rounded-xl bg-green-500 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-green-600"
        >
          <RiWhatsappLine className="size-4" />
          Share
        </a>
        <a
          href="#alerts"
          className="flex items-center gap-1.5 rounded-xl border border-ink-700 px-3 py-2 text-xs font-semibold text-ink-200 transition-colors hover:bg-ink-900"
        >
          <RiBellLine className="size-4" />
          Alert me
        </a>
      </div>
    </div>
  );
}
