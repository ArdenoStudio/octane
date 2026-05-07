import type { Messages } from "../types";

export const EN: Messages = {
  nav: {
    prices: "Prices",
    calculator: "Calculator",
    history: "History",
    changes: "Changes",
    data: "Data",
    developers: "Developers",
    getAlerts: "Get Alerts",
    menuOpen: "Open menu",
    menuClose: "Close menu",
  },
  hero: {
    live: "Live",
    cpcPricesDaily: "CPC prices updated daily",
    h1a: "Real",
    h1b: "prices.",
    h1c: "Right",
    h1d: "now.",
    sublead:
      "Sri Lanka fuel prices tracked daily from CPC — with price history, alerts, a trip calculator, and a free API.",
    ctaPrices: "Check today's prices",
    ctaAlerts: "Set a price alert",
    features: [
      {
        title: "Live prices",
        description:
          "CPC fuel prices updated daily, the moment revisions are published.",
      },
      {
        title: "Price alerts",
        description: "Set a threshold. Get emailed the instant any fuel crosses it.",
      },
      {
        title: "Trip calculator",
        description: "Distance + efficiency = your exact fuel cost at today's prices.",
      },
      {
        title: "Free API",
        description: "Open REST endpoints. No key needed for basics. Build something.",
      },
    ],
  },
  fuel: {
    petrol_92: "Petrol 92",
    petrol_95: "Petrol 95",
    auto_diesel: "Auto Diesel",
    super_diesel: "Super Diesel",
    kerosene: "Kerosene",
  },
  prices: {
    badge: "Live prices · CPC",
    title: "Sri Lanka fuel prices, today.",
    lastRevision: "Last revision",
    revisedToday: "Prices revised today",
    awaitingData: "Awaiting data",
    lkrPer: "LKR ·",
    loadError: "Couldn't load prices. The API may be offline.",
    footerSource: "Source:",
    footerLegal: " · Scraped daily at 8 AM · Independent, not affiliated.",
  },
  mobile: {
    label92: "Petrol 92 · CPC",
    shareWhatsApp: "Share",
    alertsShort: "Alerts",
    waLine:
      "🇱🇰 Petrol 92 in Sri Lanka: LKR {{price}} today.\n\nTrack all fuel prices, set alerts & calculate trip costs at octane.lk",
  },
};
