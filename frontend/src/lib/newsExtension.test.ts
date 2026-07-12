import { describe, expect, it } from "vitest";
import type { EarlySignal } from "./api";
import { applyNewsExtensions, extKey } from "./newsExtension";

const signal: EarlySignal = {
  fuel_type: "petrol_92",
  source: "news",
  price_lkr: 420,
  recorded_at: "2026-07-09",
  cpc_price_lkr: 400,
  cpc_recorded_at: "2026-06-01",
  delta_lkr: 20,
  status: "unconfirmed",
};

describe("applyNewsExtensions", () => {
  it("adds a dashed extension from last CPC revision to the media price", () => {
    const rows = [
      { date: "2026-05-01", petrol_92: 390 },
      { date: "2026-06-01", petrol_92: 400 },
      { date: "2026-06-15", petrol_92: 400 },
    ];
    const out = applyNewsExtensions(rows, [signal], ["petrol_92"], {
      today: "2026-07-10",
    });
    const start = out.find((r) => r.date === "2026-06-01");
    const mid = out.find((r) => r.date === "2026-06-15");
    const end = out.find((r) => r.date === "2026-07-09");
    expect(start?.[extKey("petrol_92")]).toBe(400);
    // Mid dates stay clear — only anchor + tip, so the chart does not stack dots.
    expect(mid?.[extKey("petrol_92")]).toBeUndefined();
    expect(end?.[extKey("petrol_92")]).toBe(420);
  });

  it("uses today when the media date is not after CPC", () => {
    const sameDay: EarlySignal = {
      ...signal,
      recorded_at: "2026-06-01",
    };
    const rows = [{ date: "2026-06-01", petrol_92: 400 }];
    const out = applyNewsExtensions(rows, [sameDay], ["petrol_92"], {
      today: "2026-07-10",
    });
    expect(out.find((r) => r.date === "2026-07-10")?.[extKey("petrol_92")]).toBe(420);
  });

  it("clamps the extension start to the visible chart range", () => {
    const rows = [
      { date: "2026-06-15", petrol_92: 400 },
      { date: "2026-06-20", petrol_92: 400 },
    ];
    const out = applyNewsExtensions(rows, [signal], ["petrol_92"], {
      today: "2026-07-10",
      rangeStart: "2026-06-15",
    });
    // Must not inject 2026-06-01 (outside 1Y/window) and blow the x-axis.
    expect(out.some((r) => r.date === "2026-06-01")).toBe(false);
    expect(out.find((r) => r.date === "2026-06-15")?.[extKey("petrol_92")]).toBe(400);
    expect(out.find((r) => r.date === "2026-07-09")?.[extKey("petrol_92")]).toBe(420);
  });

  it("still draws a stub when CPC and news share the same day", () => {
    const todaySignal: EarlySignal = {
      ...signal,
      cpc_recorded_at: "2026-07-10",
      recorded_at: "2026-07-10",
      cpc_price_lkr: 400,
      price_lkr: 420,
      delta_lkr: 20,
    };
    const rows = [{ date: "2026-07-10", petrol_92: 400 }];
    const out = applyNewsExtensions(rows, [todaySignal], ["petrol_92"], {
      today: "2026-07-10",
    });
    expect(out.find((r) => r.date === "2026-07-10")?.[extKey("petrol_92")]).toBe(400);
    expect(out.find((r) => r.date === "2026-07-11")?.[extKey("petrol_92")]).toBe(420);
  });

  it("drops the extension when there are no pending signals (CPC caught up)", () => {
    const rows = [
      { date: "2026-06-01", petrol_92: 400 },
      { date: "2026-07-09", petrol_92: 420 },
    ];
    const out = applyNewsExtensions(rows, [], ["petrol_92"], { today: "2026-07-10" });
    expect(out.every((r) => r[extKey("petrol_92")] == null)).toBe(true);
    expect(out).toEqual(rows);
  });

  it("ignores zero-delta signals", () => {
    const flat: EarlySignal = { ...signal, price_lkr: 400, delta_lkr: 0 };
    const rows = [{ date: "2026-06-01", petrol_92: 400 }];
    const out = applyNewsExtensions(rows, [flat], ["petrol_92"], { today: "2026-07-10" });
    expect(out.every((r) => r[extKey("petrol_92")] == null)).toBe(true);
  });
});
