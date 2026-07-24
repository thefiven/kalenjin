import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgendaList } from "@/components/agenda-list";
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

describe("AgendaList", () => {
  it("renders one entry per activity, with its sport", () => {
    render(
      <AgendaList
        activities={[activity({ garmin_activity_id: "1", sport: "running" })]}
      />,
    );

    expect(screen.getByText("running")).toBeInTheDocument();
  });

  it("links each entry to its detail page", () => {
    render(<AgendaList activities={[activity({ garmin_activity_id: "42" })]} />);

    expect(screen.getByRole("link")).toHaveAttribute("href", "/agenda/42");
  });

  it("shows an empty state when there are no activities", () => {
    render(<AgendaList activities={[]} />);

    expect(screen.getByText(/no session/i)).toBeInTheDocument();
  });
});
