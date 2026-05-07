import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { TripCalculator } from "./TripCalculator";
import { LocaleProvider } from "../i18n/LocaleProvider";

const { tripMock } = vi.hoisted(() => ({ tripMock: vi.fn() }));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      trip: tripMock,
    },
  };
});

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("TripCalculator", () => {
  beforeEach(() => {
    tripMock.mockReset();
    tripMock.mockResolvedValue({
      fuel_type: "petrol_92",
      distance_km: 100,
      efficiency_km_per_l: 10,
      price_lkr_per_l: 400,
      litres_needed: 10,
      cost_lkr: 4000,
      price_recorded_at: "2024-01-01T00:00:00Z",
    });
  });

  it("shows validation error when distance is not positive", async () => {
    const user = userEvent.setup();
    renderWithLocale(<TripCalculator />);
    await user.clear(screen.getByLabelText(/distance/i));
    await user.type(screen.getByLabelText(/distance/i), "0");
    await user.click(screen.getByRole("button", { name: /calculate/i }));
    expect(tripMock).not.toHaveBeenCalled();
    expect(screen.getByText(/enter positive numbers/i)).toBeInTheDocument();
  });

  it("calls API and shows trip cost on success", async () => {
    const user = userEvent.setup();
    renderWithLocale(<TripCalculator />);
    await user.click(screen.getByRole("button", { name: /calculate/i }));
    await waitFor(() => expect(tripMock).toHaveBeenCalledWith(115, 12, "petrol_92"));
    await waitFor(() => {
      expect(screen.getByText(/this trip costs/i)).toBeInTheDocument();
    });
  });
});
