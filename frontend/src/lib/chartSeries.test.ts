import { describe, expect, it } from "vitest";
import { buildForwardFilledSeries } from "./chartSeries";

describe("buildForwardFilledSeries", () => {
  it("forward-fills so a drop appears as a step, not a gap", () => {
    const rows = buildForwardFilledSeries(
      {
        petrol_92: [
          { recorded_at: "2026-05-31", price_lkr: 434 },
          { recorded_at: "2026-06-30", price_lkr: 414 },
        ],
        auto_diesel: [
          { recorded_at: "2026-05-31", price_lkr: 407 },
          { recorded_at: "2026-06-15", price_lkr: 400 },
          { recorded_at: "2026-06-30", price_lkr: 382 },
        ],
      },
      ["petrol_92", "auto_diesel"]
    );

    expect(rows).toEqual([
      { date: "2026-05-31", petrol_92: 434, auto_diesel: 407 },
      { date: "2026-06-15", petrol_92: 434, auto_diesel: 400 },
      { date: "2026-06-30", petrol_92: 414, auto_diesel: 382 },
    ]);
  });

  it("keeps unchanged fuels flat across a revision date", () => {
    const rows = buildForwardFilledSeries(
      {
        petrol_95: [
          { recorded_at: "2026-05-31", price_lkr: 495 },
          { recorded_at: "2026-06-30", price_lkr: 495 },
        ],
        petrol_92: [
          { recorded_at: "2026-05-31", price_lkr: 434 },
          { recorded_at: "2026-06-30", price_lkr: 414 },
        ],
      },
      ["petrol_92", "petrol_95"]
    );
    expect(rows[0].petrol_95).toBe(495);
    expect(rows[1].petrol_95).toBe(495);
    expect(rows[1].petrol_92).toBe(414);
  });
});
