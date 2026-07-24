import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActivityDetail } from "@/components/activity-detail";
import { activity } from "@/test-support/fixtures";

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
