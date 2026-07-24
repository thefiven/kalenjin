import type { Activity, Rapport } from "@/lib/types";

export function activity(overrides: Partial<Activity> = {}): Activity {
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

export function rapport(overrides: Partial<Rapport> = {}): Rapport {
  return {
    garmin_activity_id: "1",
    strengths: "Solid, even pacing throughout.",
    improvements: "Consider adding a warm-up next time.",
    generated_at: "2024-06-05T08:00:00",
    ...overrides,
  };
}
