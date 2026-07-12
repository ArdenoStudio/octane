import { describe, expect, it } from "vitest";
import {
  deriveEarlySignals,
  pickOfficial,
  PriceRow,
  resolveEarlySignals,
  resolveOfficialPrices,
} from "./api";

const base: PriceRow[] = [
  {
    fuel_type: "petrol_92",
    source: "cpc",
    price_lkr: 400,
    recorded_at: "2026-06-01",
  },
];

describe("pickOfficial", () => {
  it("prefers the more recently revised source", () => {
    const cpc: PriceRow = {
      fuel_type: "petrol_92",
      source: "cpc",
      price_lkr: 400,
      recorded_at: "2026-06-01",
    };
    const ioc: PriceRow = {
      fuel_type: "petrol_92",
      source: "lanka_ioc",
      price_lkr: 420,
      recorded_at: "2026-07-11",
    };
    expect(pickOfficial(cpc, ioc)?.source).toBe("lanka_ioc");
  });

  it("ties on date prefer CPC when scraped_at is missing", () => {
    const cpc: PriceRow = {
      fuel_type: "petrol_92",
      source: "cpc",
      price_lkr: 400,
      recorded_at: "2026-07-01",
    };
    const ioc: PriceRow = {
      fuel_type: "petrol_92",
      source: "lanka_ioc",
      price_lkr: 405,
      recorded_at: "2026-07-01",
    };
    expect(pickOfficial(cpc, ioc)?.source).toBe("cpc");
  });
});

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
    expect(signals[0].official_source).toBe("cpc");
  });

  it("does not treat Lanka IOC as an unconfirmed early signal", () => {
    const rows: PriceRow[] = [
      ...base,
      {
        fuel_type: "petrol_92",
        source: "lanka_ioc",
        price_lkr: 420,
        recorded_at: "2026-07-11",
      },
    ];
    expect(deriveEarlySignals(rows)).toHaveLength(0);
    expect(resolveOfficialPrices({ prices: rows })[0].source).toBe("lanka_ioc");
  });

  it("compares news against the winning LIOC official", () => {
    const rows: PriceRow[] = [
      ...base,
      {
        fuel_type: "petrol_92",
        source: "lanka_ioc",
        price_lkr: 414,
        recorded_at: "2026-07-10",
      },
      {
        fuel_type: "petrol_92",
        source: "news",
        price_lkr: 434,
        recorded_at: "2026-07-11",
      },
    ];
    const signals = deriveEarlySignals(rows);
    expect(signals).toHaveLength(1);
    expect(signals[0].official_source).toBe("lanka_ioc");
    expect(signals[0].delta_lkr).toBe(20);
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
