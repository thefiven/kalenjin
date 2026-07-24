import { describe, expect, it } from "vitest";
import { groupBySport, recentPaceBySport, weeklyDistance } from "@/lib/trends";
import { activity } from "@/test-support/fixtures";

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

describe("recentPaceBySport", () => {
  it("returns the N most recent sessions per sport, oldest first, with pace in seconds/km", () => {
    const activities = [
      activity({
        garmin_activity_id: "1",
        sport: "running",
        started_at: "2024-06-01T07:00:00",
        distance_meters: 5000,
        duration_seconds: 1500, // 5 min/km
      }),
      activity({
        garmin_activity_id: "2",
        sport: "running",
        started_at: "2024-06-03T07:00:00",
        distance_meters: 5000,
        duration_seconds: 1400,
      }),
      activity({
        garmin_activity_id: "3",
        sport: "cycling",
        started_at: "2024-06-02T07:00:00",
        distance_meters: 20000,
        duration_seconds: 3600,
      }),
    ];

    const result = recentPaceBySport(activities, 5);

    expect(result).toEqual({
      running: [
        { startedAt: "2024-06-01T07:00:00", paceSecondsPerKm: 300 },
        { startedAt: "2024-06-03T07:00:00", paceSecondsPerKm: 280 },
      ],
      cycling: [{ startedAt: "2024-06-02T07:00:00", paceSecondsPerKm: 180 }],
    });
  });

  it("caps the number of sessions per sport at the given limit, keeping the most recent", () => {
    const activities = [
      activity({ garmin_activity_id: "1", started_at: "2024-06-01T07:00:00" }),
      activity({ garmin_activity_id: "2", started_at: "2024-06-02T07:00:00" }),
      activity({ garmin_activity_id: "3", started_at: "2024-06-03T07:00:00" }),
    ];

    const result = recentPaceBySport(activities, 2);

    expect(result.running.map((p) => p.startedAt)).toEqual([
      "2024-06-02T07:00:00",
      "2024-06-03T07:00:00",
    ]);
  });

  it("skips sessions with no distance, since pace can't be computed", () => {
    const activities = [activity({ garmin_activity_id: "1", distance_meters: null })];

    const result = recentPaceBySport(activities, 5);

    expect(result).toEqual({});
  });
});
