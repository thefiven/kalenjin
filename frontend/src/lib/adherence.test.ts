import { describe, expect, it } from "vitest";
import { planAdherence } from "@/lib/adherence";
import { seance } from "@/test-support/fixtures";

describe("planAdherence", () => {
  it("returns null when there is no resolved seance yet", () => {
    expect(planAdherence([seance({ status: "pending" })])).toBeNull();
  });

  it("returns null for an empty plan", () => {
    expect(planAdherence([])).toBeNull();
  });

  it("ignores coarse weeks and still-pending seances", () => {
    const seances = [
      seance({ id: 1, detail: "coarse", status: "pending" }),
      seance({ id: 2, detail: "detailed", status: "pending" }),
      seance({ id: 3, detail: "detailed", status: "completed" }),
    ];

    expect(planAdherence(seances)).toEqual({ completedCount: 1, totalCount: 1, ratio: 1 });
  });

  it("computes the ratio of completed over completed-plus-skipped", () => {
    const seances = [
      seance({ id: 1, status: "completed" }),
      seance({ id: 2, status: "completed" }),
      seance({ id: 3, status: "skipped" }),
    ];

    expect(planAdherence(seances)).toEqual({ completedCount: 2, totalCount: 3, ratio: 2 / 3 });
  });
});
