import { describe, expect, it } from "vitest";
import { addWeeks, weekBounds } from "@/lib/date-range";

describe("weekBounds", () => {
  it("returns the Monday-Sunday bounds of the week containing the given date", () => {
    // Wednesday 2024-06-05 falls in the week of Monday 2024-06-03 to Sunday 2024-06-09
    expect(weekBounds("2024-06-05")).toEqual({ since: "2024-06-03", until: "2024-06-09" });
  });

  it("treats a Monday as the start of its own week", () => {
    expect(weekBounds("2024-06-03")).toEqual({ since: "2024-06-03", until: "2024-06-09" });
  });

  it("treats a Sunday as the end of its own week", () => {
    expect(weekBounds("2024-06-09")).toEqual({ since: "2024-06-03", until: "2024-06-09" });
  });
});

describe("addWeeks", () => {
  it("shifts a date forward by N weeks", () => {
    expect(addWeeks("2024-06-03", 1)).toBe("2024-06-10");
  });

  it("shifts a date backward for negative N", () => {
    expect(addWeeks("2024-06-03", -1)).toBe("2024-05-27");
  });
});
