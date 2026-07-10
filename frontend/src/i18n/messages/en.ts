import type { Messages } from "../types";

export const EN: Messages = {
  nav: {
    mainNavAria: "Main navigation",
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
    cpcPricesDaily: "Checked 5× daily from CPC",
    h1a: "Real",
    h1b: "prices.",
    h1c: "Right",
    h1d: "now.",
    sublead:
      "Sri Lanka fuel prices checked throughout the day from CPC — with price history, alerts, a trip calculator, and a free API.",
    ctaPrices: "Check today's prices",
    ctaAlerts: "Set a price alert",
    features: [
      {
        title: "Live prices",
        description:
          "We check CPC several times a day and surface revisions the moment they are published.",
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
    lastRevision: "Last CPC revision",
    lastChecked: "Last checked",
    revisedToday: "Prices revised today",
    earlySignalTitle: "Reported ahead of CPC",
    earlySignalNews: "News",
    earlySignalLioc: "Lanka IOC",
    earlySignalUnconfirmed: "Unconfirmed — awaiting CPC",
    mediaReports: "Media reports",
    awaitingData: "Awaiting data",
    lkrPer: "LKR ·",
    loadError: "Couldn't load prices. The API may be offline.",
    footerSource: "Source:",
    footerLegal:
      " · Checked 5× daily · Revision dates follow CPC · Independent, not affiliated.",
  },
  mobile: {
    label92: "Petrol 92 · CPC",
    shareWhatsApp: "Share",
    alertsShort: "Alerts",
    waLine:
      "🇱🇰 Petrol 92 in Sri Lanka: LKR {{price}} today.\n\nTrack all fuel prices, set alerts & calculate trip costs at octane-smoky.vercel.app",
  },
};
