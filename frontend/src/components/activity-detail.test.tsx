import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActivityDetail } from "@/components/activity-detail";
import { activity, rapport } from "@/test-support/fixtures";

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

  it("renders the rapport when one was generated", () => {
    render(
      <ActivityDetail activity={activity()} rapport={rapport({ strengths: "Good pace." })} />,
    );

    expect(screen.getByText("Good pace.")).toBeInTheDocument();
  });

  it("renders a placeholder when no rapport was generated yet", () => {
    render(<ActivityDetail activity={activity()} />);

    expect(screen.getByText(/no rapport/i)).toBeInTheDocument();
  });
});
