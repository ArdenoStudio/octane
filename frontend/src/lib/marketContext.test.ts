import { describe, expect, it } from "vitest";
import { composeMarketContext, ComparisonResp, SentimentData } from "./api";

const sentiment: SentimentData = {
  direction: "up",
  confidence: 0.8,
  magnitude_lkr: 25,
  summary: "Fuel prices likely to increase",
  generated_at: "2026-05-10T15:22:11.517855+00:00",
  headlines_analyzed: 30,
  signals: ["oil tension"],
};

const world: ComparisonResp = {
  fuel_type: "petrol_95",
  fuel_category: "gasoline",
  sri_lanka: { price_lkr: 495, price_usd: 1.476, recorded_at: "2026-06-30" },
  world_average_usd: 1.673,
  delta_vs_world_pct: -11.8,
  neighbors: [],
  fx_rate_used: 335.4113,
};

describe("composeMarketContext", () => {
  it("maps sentiment + world into the homepage strip payload", () => {
    const out = composeMarketContext("petrol_95", sentiment, world, "2026-07-12");
    expect(out.as_of).toBe("2026-07-12");
    expect(out.sentiment?.direction).toBe("up");
    expect(out.fx).toEqual({ usd_lkr: 335.4113, recorded_at: "2026-06-30" });
    expect(out.world?.delta_vs_world_pct).toBe(-11.8);
    expect(out.world?.world_average_usd).toBe(1.673);
  });

  it("tolerates missing pieces so the strip can still render partial cards", () => {
    const out = composeMarketContext("petrol_95", null, null, "2026-07-12");
    expect(out.sentiment).toBeNull();
    expect(out.fx).toBeNull();
    expect(out.world).toBeNull();
  });
});
