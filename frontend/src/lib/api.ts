const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ||
  "http://localhost:8000";

export type FuelId =
  | "petrol_92"
  | "petrol_95"
  | "auto_diesel"
  | "super_diesel"
  | "kerosene";

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

export interface PriceRow {
  fuel_type: FuelId;
  source: string;
  price_lkr: number;
  recorded_at: string;
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

export interface ForecastResp {
  fuel_type: FuelId;
  source: string;
  r_squared: number | null;
  slope_lkr_per_day: number | null;
  regression_points: ForecastPoint[];
  forecast_points: ForecastPoint[];
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

export interface ManageAlertResp {
  id: number;
  email: string;
  fuel_type: FuelId;
  threshold: number;
  direction: "above" | "below";
  active: boolean;
  created_at: string;
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

async function del<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${path}: ${r.status} ${text}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  latest: () => get<{ prices: PriceRow[] }>("/v1/prices/latest"),
  history: (fuel: FuelId, days = 730) =>
    get<{ points: HistoryPoint[] }>(`/v1/prices/history?fuel=${fuel}&days=${days}`),
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
  changes: (limit = 200) =>
    get<{ source: string; changes: PriceChangeRow[] }>(
      `/v1/prices/changes?limit=${limit}`
    ),
  manageAlert: (token: string) =>
    get<ManageAlertResp>(
      `/v1/alerts/manage?token=${encodeURIComponent(token)}`
    ),
  unsubscribeAlert: (token: string) =>
    del<{ ok: boolean; message: string }>(
      `/v1/alerts/manage?token=${encodeURIComponent(token)}`
    ),
  historyCsvUrl: (fuels: FuelId[], days: number): string => {
    const params = new URLSearchParams();
    fuels.forEach((f) => params.append("fuel", f));
    params.set("days", String(days));
    return `${API_BASE}/v1/prices/history.csv?${params.toString()}`;
  },
  subscribeDigest: (email: string) =>
    post<{ ok: boolean; id: number }>("/v1/digest/subscribe", { email }),
  historyJsonUrl: (fuels: FuelId[], days: number): string => {
    const params = new URLSearchParams();
    fuels.forEach((f) => params.append("fuel", f));
    params.set("days", String(days));
    return `${API_BASE}/v1/prices/history.json?${params.toString()}`;
  },
  apiBase: API_BASE,
};
