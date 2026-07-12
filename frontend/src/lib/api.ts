/** Production default when env is absent at build time — avoids fetching localhost from HTTPS deployments. */
const rawApiBase =
  typeof import.meta.env.VITE_API_BASE === "string" && import.meta.env.VITE_API_BASE.trim()
    ? import.meta.env.VITE_API_BASE.trim().replace(/\/$/, "")
    : import.meta.env.PROD
      ? "https://octane-api.fly.dev"
      : "http://localhost:8000";

const API_BASE = rawApiBase;

export type FuelId =
  | "petrol_92"
  | "petrol_95"
  | "auto_diesel"
  | "super_diesel"
  | "kerosene";

/** Official administered sources vs media-reported (unconfirmed) news. */
export type PriceSource = "cpc" | "news" | "lanka_ioc";
export type OfficialSource = "cpc" | "lanka_ioc";

export const FUEL_DISPLAY: Record<FuelId, string> = {
  petrol_92: "Petrol 92",
  petrol_95: "Petrol 95",
  auto_diesel: "Auto Diesel",
  super_diesel: "Super Diesel",
  kerosene: "Kerosene",
};

export const FUEL_ORDER: FuelId[] = [
  "petrol_92",
  "petrol_95",
  "auto_diesel",
  "super_diesel",
  "kerosene",
];

export const OFFICIAL_SOURCE_LABEL: Record<OfficialSource, string> = {
  cpc: "CPC",
  lanka_ioc: "Lanka IOC",
};

export interface PriceRow {
  fuel_type: FuelId;
  source: string;
  price_lkr: number;
  recorded_at: string;
  /** When Octane last wrote/verified this row (ISO timestamp), if available. */
  scraped_at?: string | null;
}

export interface EarlySignal {
  fuel_type: FuelId;
  source: "news" | string;
  price_lkr: number;
  recorded_at: string;
  scraped_at?: string | null;
  /** Winning official source the news figure is compared against. */
  official_source?: OfficialSource | string;
  official_price_lkr?: number;
  official_recorded_at?: string;
  /** Aliases of official_* for chart media extensions / older payloads. */
  cpc_price_lkr: number;
  cpc_recorded_at: string;
  delta_lkr: number;
  status: "unconfirmed" | string;
}

/** Days a news figure stays "early" after its effective date (matches backend). */
const NEWS_SIGNAL_WINDOW_DAYS = 14;

function rowBySource(
  rows: PriceRow[],
  fuel: FuelId,
  source: string
): PriceRow | undefined {
  return rows.find((r) => r.fuel_type === fuel && r.source === source);
}

function parseScrapedMs(value?: string | null): number {
  if (!value) return Number.NEGATIVE_INFINITY;
  const t = Date.parse(value);
  return Number.isFinite(t) ? t : Number.NEGATIVE_INFINITY;
}

/**
 * Pick the more recently revised official price between CPC and Lanka IOC.
 * Tie on recorded_at → newer scraped_at, then prefer CPC.
 */
export function pickOfficial(
  cpc: PriceRow | undefined,
  ioc: PriceRow | undefined
): PriceRow | undefined {
  if (!cpc && !ioc) return undefined;
  if (!cpc) return ioc;
  if (!ioc) return cpc;
  if (ioc.recorded_at > cpc.recorded_at) return ioc;
  if (cpc.recorded_at > ioc.recorded_at) return cpc;
  if (parseScrapedMs(ioc.scraped_at) > parseScrapedMs(cpc.scraped_at)) return ioc;
  return cpc;
}

/** Resolve official prices from a latest payload (API `official` or local pick). */
export function resolveOfficialPrices(resp: LatestPricesResp): PriceRow[] {
  if (resp.official && resp.official.length > 0) return resp.official;
  return FUEL_ORDER.map((fuel) =>
    pickOfficial(rowBySource(resp.prices, fuel, "cpc"), rowBySource(resp.prices, fuel, "lanka_ioc"))
  ).filter((r): r is PriceRow => !!r);
}

/**
 * Derive early signals from a latest-prices payload.
 * Prefer API `early_signals` when present; otherwise compare news vs the
 * winning official (CPC or LIOC).
 */
export function resolveEarlySignals(resp: LatestPricesResp): EarlySignal[] {
  if (resp.early_signals && resp.early_signals.length > 0) {
    return resp.early_signals;
  }
  return deriveEarlySignals(resp.prices);
}

export function deriveEarlySignals(rows: PriceRow[]): EarlySignal[] {
  const today = new Date();
  const cutoff = new Date(today);
  cutoff.setDate(cutoff.getDate() - NEWS_SIGNAL_WINDOW_DAYS);
  const cutoffStr = cutoff.toISOString().slice(0, 10);
  const out: EarlySignal[] = [];

  for (const fuel of FUEL_ORDER) {
    const official = pickOfficial(
      rowBySource(rows, fuel, "cpc"),
      rowBySource(rows, fuel, "lanka_ioc")
    );
    if (!official) continue;

    const news = rowBySource(rows, fuel, "news");
    if (!news) continue;

    const differs = Math.abs(news.price_lkr - official.price_lkr) >= 0.01;
    const newerOrSame = news.recorded_at >= official.recorded_at;
    const recent = news.recorded_at >= cutoffStr;
    if (recent && newerOrSame && (news.recorded_at > official.recorded_at || differs)) {
      out.push({
        fuel_type: fuel,
        source: "news",
        price_lkr: news.price_lkr,
        recorded_at: news.recorded_at,
        scraped_at: news.scraped_at,
        official_source: official.source,
        official_price_lkr: official.price_lkr,
        official_recorded_at: official.recorded_at,
        cpc_price_lkr: official.price_lkr,
        cpc_recorded_at: official.recorded_at,
        delta_lkr: Math.round((news.price_lkr - official.price_lkr) * 100) / 100,
        status: "unconfirmed",
      });
    }
  }

  return out;
}

export interface LatestPricesResp {
  prices: PriceRow[];
  /** Per-fuel official pick (CPC vs Lanka IOC). */
  official?: PriceRow[];
  /** Fresher of CPC / Lanka IOC scrape checks. */
  last_verified_at?: string | null;
  last_verified_by_source?: {
    cpc?: string | null;
    lanka_ioc?: string | null;
  };
  /** News figures ahead of the winning official source. */
  early_signals?: EarlySignal[];
}

export interface MarketContextResp {
  as_of: string;
  fuel_type: FuelId;
  sentiment: SentimentData | null;
  fx: { usd_lkr: number; recorded_at: string } | null;
  world: {
    fuel_type: FuelId;
    sri_lanka_usd: number | null;
    world_average_usd: number | null;
    delta_vs_world_pct: number | null;
    fx_rate_used: number;
  } | null;
}

/** Build market-context payload from endpoints available on older API deploys. */
export function composeMarketContext(
  fuel: FuelId,
  sentiment: SentimentData | null,
  world: ComparisonResp | null,
  asOf: string = new Date().toISOString().slice(0, 10),
): MarketContextResp {
  return {
    as_of: asOf,
    fuel_type: fuel,
    sentiment,
    fx: world
      ? {
          usd_lkr: world.fx_rate_used,
          recorded_at: world.sri_lanka.recorded_at ?? asOf,
        }
      : null,
    world: world
      ? {
          fuel_type: world.fuel_type,
          sri_lanka_usd: world.sri_lanka.price_usd,
          world_average_usd: world.world_average_usd,
          delta_vs_world_pct: world.delta_vs_world_pct,
          fx_rate_used: world.fx_rate_used,
        }
      : null,
  };
}

/** Daily Groq output committed to master by .github/workflows/sentiment.yml */
export const SENTIMENT_RAW_URL =
  "https://raw.githubusercontent.com/ArdenoStudio/octane/master/backend/data/ai_sentiment.json";

/** Prefer GitHub-committed sentiment when the Fly API copy is older than this. */
export const SENTIMENT_STALE_MS = 36 * 60 * 60 * 1000;

export function isSentimentStale(
  sentiment: SentimentData | null | undefined,
  nowMs: number = Date.now(),
  maxAgeMs: number = SENTIMENT_STALE_MS,
): boolean {
  if (!sentiment?.generated_at) return true;
  const t = Date.parse(sentiment.generated_at);
  if (Number.isNaN(t)) return true;
  return nowMs - t > maxAgeMs;
}

export function parseSentimentPayload(data: unknown): SentimentData | null {
  if (!data || typeof data !== "object") return null;
  const d = data as Record<string, unknown>;
  const confidence = Number(d.confidence ?? 0);
  if (!(confidence > 0)) return null;
  const direction = String(d.direction ?? "stable");
  if (direction !== "up" && direction !== "down" && direction !== "stable") {
    return null;
  }
  return {
    direction,
    confidence,
    magnitude_lkr: Number(d.magnitude_lkr ?? 0),
    summary: String(d.summary ?? ""),
    generated_at: String(d.generated_at ?? ""),
    headlines_analyzed: Number(d.headlines_analyzed ?? 0),
    signals: Array.isArray(d.signals) ? d.signals.map(String) : [],
  };
}

/** Load the latest committed sentiment JSON from GitHub (bypasses stale Fly bake-in). */
export async function fetchCommittedSentiment(): Promise<SentimentData | null> {
  try {
    const r = await fetch(SENTIMENT_RAW_URL, { cache: "no-store" });
    if (!r.ok) return null;
    return parseSentimentPayload(await r.json());
  } catch {
    return null;
  }
}

/**
 * Prefer API sentiment when fresh; otherwise use the daily GitHub commit.
 * Sentiment is written to git daily, but Fly only serves the copy baked into
 * the last successful image deploy — which can lag for months when deploys fail.
 */
export async function preferFreshSentiment(
  apiSentiment: SentimentData | null | undefined,
): Promise<SentimentData | null> {
  if (!isSentimentStale(apiSentiment)) {
    return apiSentiment ?? null;
  }
  const committed = await fetchCommittedSentiment();
  if (!committed) return apiSentiment ?? null;
  if (!apiSentiment) return committed;
  // Both present and API is stale — keep whichever generated_at is newer.
  const apiT = Date.parse(apiSentiment.generated_at);
  const rawT = Date.parse(committed.generated_at);
  if (Number.isNaN(rawT)) return apiSentiment;
  if (Number.isNaN(apiT) || rawT >= apiT) return committed;
  return apiSentiment;
}

export interface HistoryPoint {
  recorded_at: string;
  price_lkr: number;
}

export interface ComparisonResp {
  fuel_type: FuelId;
  fuel_category: string;
  sri_lanka: { price_lkr: number | null; price_usd: number | null; recorded_at: string | null };
  world_average_usd: number | null;
  delta_vs_world_pct: number | null;
  neighbors: { country: string; price_usd: number; recorded_at: string }[];
  fx_rate_used: number;
}

export interface TripResp {
  fuel_type: FuelId;
  distance_km: number;
  efficiency_km_per_l: number;
  price_lkr_per_l: number;
  litres_needed: number;
  cost_lkr: number;
  price_recorded_at: string;
}

export interface ForecastPoint {
  date: string;
  price_lkr: number;
}

export interface SentimentData {
  direction: "up" | "down" | "stable";
  confidence: number;
  magnitude_lkr: number;
  summary: string;
  generated_at: string;
  headlines_analyzed: number;
  signals: string[];
}

export interface ForecastResp {
  fuel_type: FuelId;
  source: string;
  r_squared: number | null;
  slope_lkr_per_day: number | null;
  regression_points: ForecastPoint[];
  forecast_points: ForecastPoint[];
  ai_forecast_points: ForecastPoint[];
  sentiment: SentimentData | null;
  error?: string;
}

export interface PriceChangeRow {
  fuel_type: FuelId;
  recorded_at: string;
  price_lkr: number;
  previous_lkr: number | null;
  delta_lkr: number | null;
  delta_pct: number | null;
}

export interface AlertFire {
  fired_at: string;
  price_lkr: number;
}

export interface ManageAlertResp {
  id: number;
  email: string;
  fuel_type: FuelId;
  threshold: number;
  direction: "above" | "below";
  active: boolean;
  confirmed: boolean;
  created_at: string;
  fire_history: AlertFire[];
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${path}: ${r.status} ${text}`);
  }
  return r.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${path}: ${r.status} ${text}`);
  }
  return r.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${path}: ${r.status} ${text}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  latest: () => get<LatestPricesResp>("/v1/prices/latest"),
  marketContext: async (fuel: FuelId = "petrol_95"): Promise<MarketContextResp> => {
    const r = await fetch(`${API_BASE}/v1/market-context?fuel=${fuel}`);
    if (r.ok) {
      const data = (await r.json()) as MarketContextResp;
      // Even when the dedicated route exists, Fly may serve a months-old
      // baked-in sentiment file — refresh from the daily git commit if stale.
      data.sentiment = await preferFreshSentiment(data.sentiment);
      return data;
    }
    // Fly backend deploy has been stuck (billing) since before this route shipped.
    // Compose from endpoints that older production builds already expose.
    if (r.status === 404) {
      const [sentWrap, world] = await Promise.all([
        get<{ available: boolean; sentiment: SentimentData | null }>(
          "/v1/prices/sentiment",
        ).catch(() => ({ available: false, sentiment: null })),
        get<ComparisonResp>(`/v1/comparison/world?fuel=${fuel}`).catch(
          () => null,
        ),
      ]);
      const sentiment = await preferFreshSentiment(sentWrap.sentiment);
      return composeMarketContext(fuel, sentiment, world);
    }
    throw new Error(`/v1/market-context: ${r.status}`);
  },
  history: (fuel: FuelId, days = 730, source: PriceSource = "cpc") =>
    get<{ points: HistoryPoint[] }>(
      `/v1/prices/history?fuel=${fuel}&days=${days}&source=${source}`
    ),
  worldComparison: (fuel: FuelId) =>
    get<ComparisonResp>(`/v1/comparison/world?fuel=${fuel}`),
  trip: (distance: number, efficiency: number, fuel: FuelId) =>
    get<TripResp>(
      `/v1/calculator/trip?distance=${distance}&efficiency=${efficiency}&fuel=${fuel}`
    ),
  subscribe: (payload: {
    email: string;
    fuel_type: FuelId;
    threshold: number;
    direction: "above" | "below";
    telegram_chat_id?: string;
  }) => post<{ id: number; ok: boolean }>("/v1/alerts/subscribe", payload),
  forecast: (fuel: FuelId, historyDays = 365, horizonDays = 90) =>
    get<ForecastResp>(
      `/v1/prices/forecast?fuel=${fuel}&history_days=${historyDays}&horizon_days=${horizonDays}`
    ),
  sentiment: async () => {
    const fromApi = await get<{ available: boolean; sentiment: SentimentData | null }>(
      "/v1/prices/sentiment",
    ).catch(() => ({ available: false, sentiment: null }));
    const sentiment = await preferFreshSentiment(fromApi.sentiment);
    return { available: sentiment != null, sentiment };
  },
  changes: (limit = 200, source: PriceSource = "cpc") =>
    get<{ source: string; changes: PriceChangeRow[] }>(
      `/v1/prices/changes?limit=${limit}&source=${source}`
    ),
  confirmAlert: (token: string) =>
    get<{ ok: boolean; message: string }>(
      `/v1/alerts/confirm?token=${encodeURIComponent(token)}`
    ),
  manageAlert: (token: string) =>
    get<ManageAlertResp>(
      `/v1/alerts/manage?token=${encodeURIComponent(token)}`
    ),
  updateAlert: (token: string, payload: { threshold: number; direction: "above" | "below" }) =>
    patch<{ ok: boolean }>(
      `/v1/alerts/manage?token=${encodeURIComponent(token)}`,
      payload,
    ),
  unsubscribeAlert: (token: string) =>
    del<{ ok: boolean; message: string }>(
      `/v1/alerts/manage?token=${encodeURIComponent(token)}`
    ),
  historyCsvUrl: (fuels: FuelId[], days: number, source: PriceSource = "cpc"): string => {
    const params = new URLSearchParams();
    fuels.forEach((f) => params.append("fuel", f));
    params.set("days", String(days));
    params.set("source", source);
    return `${API_BASE}/v1/prices/history.csv?${params.toString()}`;
  },
  subscribeDigest: (email: string) =>
    post<{ ok: boolean; id: number }>("/v1/digest/subscribe", { email }),
  historyJsonUrl: (fuels: FuelId[], days: number, source: PriceSource = "cpc"): string => {
    const params = new URLSearchParams();
    fuels.forEach((f) => params.append("fuel", f));
    params.set("days", String(days));
    params.set("source", source);
    return `${API_BASE}/v1/prices/history.json?${params.toString()}`;
  },
  apiBase: API_BASE,
};
