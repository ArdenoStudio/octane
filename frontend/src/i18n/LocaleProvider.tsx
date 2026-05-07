import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { FuelId } from "../lib/api";
import { FUEL_DISPLAY } from "../lib/api";
import {
  BUNDLES,
  LOCALE_ORDER,
  LOCALE_SHORT_LABEL,
  STORAGE_KEY,
  type Locale,
  type Messages,
  resolveInitialLocale,
} from "./bundles";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  m: Messages;
  /** Localized fuel label, English fallback if missing */
  fuelLabel: (id: FuelId) => string;
  locales: readonly Locale[];
  localeShortLabel: typeof LOCALE_SHORT_LABEL;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => resolveInitialLocale());

  useEffect(() => {
    document.documentElement.lang = locale === "en" ? "en-LK" : locale === "si" ? "si-LK" : "ta-LK";
  }, [locale]);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    localStorage.setItem(STORAGE_KEY, l);
  }, []);

  const value = useMemo(() => {
    const m = BUNDLES[locale];
    function fuelLabel(id: FuelId): string {
      return m.fuel[id] ?? FUEL_DISPLAY[id];
    }
    return {
      locale,
      setLocale,
      m,
      fuelLabel,
      locales: LOCALE_ORDER,
      localeShortLabel: LOCALE_SHORT_LABEL,
    };
  }, [locale, setLocale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}

export function useFuelLabel(): (id: FuelId) => string {
  return useLocale().fuelLabel;
}
