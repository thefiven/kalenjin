import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Dashboard } from "@/components/dashboard";
import { activity } from "@/test-support/fixtures";

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

  it("does not claim to show VO2max/critical pace/training load, which aren't tracked", () => {
    render(<Dashboard activities={[activity()]} />);

    expect(screen.getByText(/aren't tracked yet/i)).toBeInTheDocument();
  });

  it("shows a recent pace trend per sport in the progression section", () => {
    render(
      <Dashboard
        activities={[
          activity({
            garmin_activity_id: "1",
            sport: "running",
            started_at: "2024-06-01T07:00:00",
            distance_meters: 5000,
            duration_seconds: 1500,
          }),
          activity({
            garmin_activity_id: "2",
            sport: "running",
            started_at: "2024-06-03T07:00:00",
            distance_meters: 5000,
            duration_seconds: 1400,
          }),
        ]}
      />,
    );

    expect(screen.getByText("5:00 /km")).toBeInTheDocument();
    expect(screen.getByText("4:40 /km")).toBeInTheDocument();
  });
});
