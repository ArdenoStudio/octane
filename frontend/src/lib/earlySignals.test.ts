import { describe, expect, it } from "vitest";
import { deriveEarlySignals, PriceRow, resolveEarlySignals } from "./api";

const base: PriceRow[] = [
  {
    fuel_type: "petrol_92",
    source: "cpc",
    price_lkr: 400,
    recorded_at: "2026-06-01",
  },
];

describe("deriveEarlySignals", () => {
  it("surfaces news ahead of CPC when the figure differs", () => {
    const rows: PriceRow[] = [
      ...base,
      {
        fuel_type: "petrol_92",
        source: "news",
        price_lkr: 414,
        recorded_at: "2026-07-09",
      },
    ];
    const signals = deriveEarlySignals(rows);
    expect(signals).toHaveLength(1);
    expect(signals[0].delta_lkr).toBe(14);
    expect(signals[0].status).toBe("unconfirmed");
  });

  it("ignores news that matches an already-revised CPC price", () => {
    const rows: PriceRow[] = [
      {
        fuel_type: "petrol_92",
        source: "cpc",
        price_lkr: 414,
        recorded_at: "2026-06-30",
      },
      {
        fuel_type: "petrol_92",
        source: "news",
        price_lkr: 414,
        recorded_at: "2026-06-29",
      },
    ];
    expect(deriveEarlySignals(rows)).toHaveLength(0);
  });

  it("prefers API early_signals when present", () => {
    const resolved = resolveEarlySignals({
      prices: base,
      early_signals: [
        {
          fuel_type: "petrol_92",
          source: "news",
          price_lkr: 410,
          recorded_at: "2026-07-09",
          cpc_price_lkr: 400,
          cpc_recorded_at: "2026-06-01",
          delta_lkr: 10,
          status: "unconfirmed",
        },
      ],
    });
    expect(resolved).toHaveLength(1);
    expect(resolved[0].price_lkr).toBe(410);
  });
});
