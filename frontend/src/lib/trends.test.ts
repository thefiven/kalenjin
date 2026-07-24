import { describe, expect, it } from "vitest";
import { groupBySport, weeklyDistance } from "@/lib/trends";
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

describe("groupBySport", () => {
  it("counts sessions and sums distance per sport", () => {
    const activities = [
      activity({ garmin_activity_id: "1", sport: "running", distance_meters: 5000 }),
      activity({ garmin_activity_id: "2", sport: "running", distance_meters: 10000 }),
      activity({ garmin_activity_id: "3", sport: "cycling", distance_meters: 20000 }),
    ];

    const result = groupBySport(activities);

    expect(result).toEqual({
      running: { count: 2, totalDistanceMeters: 15000 },
      cycling: { count: 1, totalDistanceMeters: 20000 },
    });
  });

  it("returns an empty object for no activities", () => {
    expect(groupBySport([])).toEqual({});
  });
});

describe("weeklyDistance", () => {
  it("sums distance per ISO week, most recent week first", () => {
    const activities = [
      // Monday 2024-06-03 and Wednesday 2024-06-05 both fall in ISO week 2024-W23
      activity({ garmin_activity_id: "1", started_at: "2024-06-03T07:00:00", distance_meters: 5000 }),
      activity({ garmin_activity_id: "2", started_at: "2024-06-05T07:00:00", distance_meters: 3000 }),
      // Monday 2024-06-10 falls in the following ISO week 2024-W24
      activity({ garmin_activity_id: "3", started_at: "2024-06-10T07:00:00", distance_meters: 8000 }),
    ];

    const result = weeklyDistance(activities);

    expect(result).toEqual([
      { week: "2024-W24", totalDistanceMeters: 8000 },
      { week: "2024-W23", totalDistanceMeters: 8000 },
    ]);
  });
});
