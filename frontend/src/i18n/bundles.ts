import type { Locale } from "./types";
import { EN } from "./messages/en";
import { SI } from "./messages/si";
import { TA } from "./messages/ta";

export type { Locale, Messages } from "./types";

export const BUNDLES: Record<Locale, typeof EN> = {
  en: EN,
  si: SI,
  ta: TA,
};

export const LOCALE_ORDER: Locale[] = ["en", "si", "ta"];

export const LOCALE_SHORT_LABEL: Record<Locale, string> = {
  en: "EN",
  si: "සිං",
  ta: "தமிழ்",
};

const STORAGE_KEY = "octane.locale";

function readStoredLocale(): Locale | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === "en" || raw === "si" || raw === "ta") return raw;
  return null;
}

export function resolveInitialLocale(): Locale {
  const stored = readStoredLocale();
  if (stored) return stored;
  if (typeof navigator !== "undefined") {
    const lang = navigator.language?.slice(0, 2).toLowerCase();
    if (lang === "si") return "si";
    if (lang === "ta") return "ta";
  }
  return "en";
}

export { STORAGE_KEY };
