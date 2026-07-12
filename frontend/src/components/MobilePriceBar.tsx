import { useEffect, useState } from "react";
import { RiBellLine, RiWhatsappLine } from "@remixicon/react";
import { api, OFFICIAL_SOURCE_LABEL, PriceRow, resolveOfficialPrices } from "../lib/api";
import { useLocale } from "../i18n/LocaleProvider";
import { lkr } from "../lib/format";

export function MobilePriceBar() {
  const { m } = useLocale();
  const [price92, setPrice92] = useState<PriceRow | null>(null);

  useEffect(() => {
    api
      .latest()
      .then((r) => {
        const official = resolveOfficialPrices(r).find((p) => p.fuel_type === "petrol_92");
        if (official) setPrice92(official);
      })
      .catch(() => {});
  }, []);

  if (!price92) return null;

  const sourceLabel =
    price92.source === "lanka_ioc"
      ? OFFICIAL_SOURCE_LABEL.lanka_ioc
      : OFFICIAL_SOURCE_LABEL.cpc;
  const waRaw = m.mobile.waLine.replace(/\{\{price\}\}/g, String(price92.price_lkr));

  const waText = encodeURIComponent(waRaw);

  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 flex items-center justify-between gap-3 border-t border-ink-800 bg-white/95 px-4 py-3 backdrop-blur-sm sm:hidden">
      <div>
        <div className="text-xs text-ink-400">
          Petrol 92 · {sourceLabel}
        </div>
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
          {m.mobile.shareWhatsApp}
        </a>
        <a
          href="#alerts"
          className="flex items-center gap-1.5 rounded-xl border border-ink-700 px-3 py-2 text-xs font-semibold text-ink-200 transition-colors hover:bg-ink-900"
        >
          <RiBellLine className="size-4" />
          {m.mobile.alertsShort}
        </a>
      </div>
    </div>
  );
}
