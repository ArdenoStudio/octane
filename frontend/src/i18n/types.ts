import type { FuelId } from "../lib/api";

export type Locale = "en" | "si" | "ta";

export interface Messages {
  nav: {
    prices: string;
    calculator: string;
    history: string;
    changes: string;
    data: string;
    developers: string;
    getAlerts: string;
    menuOpen: string;
    menuClose: string;
  };
  hero: {
    live: string;
    cpcPricesDaily: string;
    h1a: string;
    h1b: string;
    h1c: string;
    h1d: string;
    sublead: string;
    ctaPrices: string;
    ctaAlerts: string;
    features: Array<{ title: string; description: string }>;
  };
  fuel: Record<FuelId, string>;
  prices: {
    badge: string;
    title: string;
    lastRevision: string;
    revisedToday: string;
    awaitingData: string;
    lkrPer: string;
    loadError: string;
    footerSource: string;
    footerLegal: string;
  };
  mobile: {
    label92: string;
    shareWhatsApp: string;
    alertsShort: string;
    waLine: string;
  };
}
