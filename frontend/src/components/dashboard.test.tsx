import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Dashboard } from "@/components/dashboard";
import type { Activity } from "@/lib/types";

function activity(overrides: Partial<Activity> = {}): Activity {
  return {
    garmin_activity_id: "1",
    sport: "running",
    started_at: "2024-06-05T07:30:00",
    duration_seconds: 1800,
    distance_meters: 5000,
    average_heart_rate: 150,
    ...overrides,
  };
}

describe("Dashboard", () => {
  it("renders all four trend categories", () => {
    render(<Dashboard activities={[activity()]} />);

    expect(screen.getByRole("heading", { name: /fitness trend/i })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /progression by session type/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /recovery/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /plan adherence/i })).toBeInTheDocument();
  });

  it("shows a placeholder for recovery, since no wellness data is synced yet", () => {
    render(<Dashboard activities={[activity()]} />);

    expect(screen.getByText(/no recovery data/i)).toBeInTheDocument();
  });

  it("shows a placeholder for plan adherence, since no plan exists yet", () => {
    render(<Dashboard activities={[activity()]} />);

    expect(screen.getByText(/no training plan/i)).toBeInTheDocument();
  });

  it("shows per-sport totals in the progression section", () => {
    render(
      <Dashboard
        activities={[
          activity({ garmin_activity_id: "1", sport: "running" }),
          activity({ garmin_activity_id: "2", sport: "cycling" }),
        ]}
      />,
    );

    expect(screen.getByText("running")).toBeInTheDocument();
    expect(screen.getByText("cycling")).toBeInTheDocument();
  });
});
