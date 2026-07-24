import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActivityDetail } from "@/components/activity-detail";
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

describe("ActivityDetail", () => {
  it("renders the sport and distance", () => {
    render(<ActivityDetail activity={activity({ sport: "cycling", distance_meters: 20000 })} />);

    expect(screen.getByText("cycling")).toBeInTheDocument();
    expect(screen.getByText("20.00 km")).toBeInTheDocument();
  });

  it("renders the average heart rate when present", () => {
    render(<ActivityDetail activity={activity({ average_heart_rate: 162 })} />);

    expect(screen.getByText(/162/)).toBeInTheDocument();
  });

  it("renders a placeholder when the average heart rate is missing", () => {
    render(<ActivityDetail activity={activity({ average_heart_rate: null })} />);

    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
