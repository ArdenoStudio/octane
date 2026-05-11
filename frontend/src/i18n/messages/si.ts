import type { Messages } from "../types";

export const SI: Messages = {
  nav: {
    mainNavAria: "ප්‍රධාන මෙනුව",
    prices: "මිල ගණන්",
    calculator: "ගණකය",
    history: "ඉතිහාසය",
    changes: "වෙනස්කම්",
    data: "දත්ත",
    developers: "සංවර්ධක",
    getAlerts: "ඇලර්ට්",
    menuOpen: "මෙනුව අරින්න",
    menuClose: "මෙනුව වැසෙන්න",
  },
  hero: {
    live: "සජීවී",
    cpcPricesDaily: "දිනපතා CPC මිල ගණන් යාවත්කාලීනයි",
    h1a: "තහවුරු",
    h1b: "මිල ගණන්.",
    h1c: "මේ",
    h1d: "මොහොතේම.",
    sublead:
      "CPC වෙතින් ශ්‍රී ලංකාවේ ඉන්ධන මිල ගණන් දිනපතා — ඉතිහාස ලේඛන, විදියන්න විද හරහා ගණන හා විවෘත API ද සමග.",
    ctaPrices: "අද මිල බලන්න",
    ctaAlerts: "විදිය විද ගන්න විද ගහන වෙලාවට",
    features: [
      {
        title: "සජීව මිල",
        description: "සංශෝධන ප්‍රකාශය වූ විගස CPC ඉන්ධන මිල යාවත්කාලීනයි.",
      },
      {
        title: "මිල විදියන්න",
        description: "සීමාවක් තෝරන්න — ඉන්ධනය මාරු වූ ක්‍ෂණයෙන් විදියෙන් ලැබෙයි.",
      },
      {
        title: "ගමන ගණනය",
        description: "දුර + වාහන කාර්යක්ෂමතාව — අද මිලින් ගමන් වියදම්.",
      },
      {
        title: "නොමිලේ API",
        description: "විවෘත REST. මූලික කාර්යයන්ට යතුරක් අවශ්‍ය නැහැ.",
      },
    ],
  },
  fuel: {
    petrol_92: "පෙට්රල් 92",
    petrol_95: "පෙට්රල් 95",
    auto_diesel: "ස්වයං ඩීසල්",
    super_diesel: "සුපිරි ඩීසල්",
    kerosene: "කිරොසීන්",
  },
  prices: {
    badge: "සජීව මිල · CPC",
    title: "අද ශ්‍රී ලංකා ඉන්ධන මිල ගණන්.",
    lastRevision: "අන්තර්ගත සංශෝධනය",
    revisedToday: "අද මිල ගණන් වෙනස්කම් ඇති විය",
    awaitingData: "දත්ත එනකම් බලන්නේ",
    lkrPer: "රු. ·",
    loadError:
      "මිල පූරණය නොහැක. API අබල හෝ බද්දට සම්බන්ධතා ගැටලුවක් විය හැක.",
    footerSource: "මූලාශ්‍රය:",
    footerLegal:
      " · දිනපතා උදේ 8ට පමණ කාලසටහන · CPC සමඟ අනුබද්ධ නොවන ස්වාධීන ව්‍යාපෘතියකි.",
  },
  mobile: {
    label92: "පෙට්රල් 92 · CPC",
    shareWhatsApp: "බෙදාගන්න",
    alertsShort: "විදියන්න",
    waLine:
      "🇱🇰 ශ්‍රී ලංකාවේ පෙට්රල් 92 අද රු. {{price}}.\n\nසියලු ඉන්ධන මිල, විදියන්න හා ගමන ගණන octane-smoky.vercel.app හි",
  },
};
