import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PlanView } from "@/components/plan-view";
import { seance } from "@/test-support/fixtures";

vi.mock("@/app/plan/actions", () => ({
  updateSeanceAction: vi.fn(),
}));

const objectif = {
  id: 1,
  sport: "running",
  target_distance_meters: 10000,
  target_date: "2026-09-01",
  target_time_seconds: null,
};

describe("PlanView", () => {
  it("shows the objectif summary", () => {
    render(<PlanView objectif={objectif} seances={[]} />);

    expect(screen.getByText(/running/i)).toBeInTheDocument();
    expect(screen.getByText(/2026-09-01/)).toBeInTheDocument();
  });

  it("shows a coarse week's theme instead of individual sessions", () => {
    render(
      <PlanView
        objectif={objectif}
        seances={[
          seance({
            id: 1,
            detail: "coarse",
            scheduled_date: null,
            theme: "Base — ~20km target volume",
          }),
        ]}
      />,
    );

    expect(screen.getByText("Base — ~20km target volume")).toBeInTheDocument();
  });

  it("shows one editable row per detailed session", () => {
    render(
      <PlanView
        objectif={objectif}
        seances={[
          seance({ id: 1, scheduled_date: "2026-01-05" }),
          seance({ id: 2, scheduled_date: "2026-01-07" }),
        ]}
      />,
    );

    expect(screen.getByText("2026-01-05")).toBeInTheDocument();
    expect(screen.getByText("2026-01-07")).toBeInTheDocument();
    expect(screen.getAllByText("Save")).toHaveLength(2);
  });

  it("shows the completion status of each session", () => {
    render(
      <PlanView
        objectif={objectif}
        seances={[seance({ id: 1, status: "completed" })]}
      />,
    );

    expect(screen.getByText("completed")).toBeInTheDocument();
  });
});
