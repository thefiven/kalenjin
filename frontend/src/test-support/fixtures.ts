import type { Activity, Rapport, Seance } from "@/lib/types";

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

export function seance(overrides: Partial<Seance> = {}): Seance {
  return {
    id: 1,
    week_start: "2024-06-03",
    phase: "base",
    detail: "detailed",
    scheduled_date: "2024-06-05",
    seance_type: "easy",
    distance_meters: 5000,
    theme: null,
    week_volume_meters: 20000,
    status: "pending",
    garmin_activity_id: null,
    ...overrides,
  };
}
