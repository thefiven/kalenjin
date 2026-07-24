import type { Activity } from "@/lib/types";

export interface SportSummary {
  count: number;
  totalDistanceMeters: number;
}

export function groupBySport(activities: Activity[]): Record<string, SportSummary> {
  const result: Record<string, SportSummary> = {};

  for (const activity of activities) {
    const existing = result[activity.sport] ?? { count: 0, totalDistanceMeters: 0 };
    result[activity.sport] = {
      count: existing.count + 1,
      totalDistanceMeters: existing.totalDistanceMeters + (activity.distance_meters ?? 0),
    };
  }

  return result;
}

export interface WeeklyDistance {
  week: string;
  totalDistanceMeters: number;
}

export function weeklyDistance(activities: Activity[]): WeeklyDistance[] {
  const totals = new Map<string, number>();

  for (const activity of activities) {
    const week = isoWeekKey(new Date(activity.started_at));
    totals.set(week, (totals.get(week) ?? 0) + (activity.distance_meters ?? 0));
  }

  return Array.from(totals.entries())
    .sort(([a], [b]) => (a < b ? 1 : -1))
    .map(([week, totalDistanceMeters]) => ({ week, totalDistanceMeters }));
}

export interface PacePoint {
  startedAt: string;
  paceSecondsPerKm: number;
}

export function recentPaceBySport(
  activities: Activity[],
  limit: number,
): Record<string, PacePoint[]> {
  const bySport: Record<string, PacePoint[]> = {};

  const withPace = activities
    .filter((a): a is Activity & { distance_meters: number } => (a.distance_meters ?? 0) > 0)
    .sort((a, b) => (a.started_at < b.started_at ? -1 : 1));

  for (const a of withPace) {
    const points = (bySport[a.sport] ??= []);
    points.push({
      startedAt: a.started_at,
      paceSecondsPerKm: a.duration_seconds / (a.distance_meters / 1000),
    });
  }

  for (const sport of Object.keys(bySport)) {
    bySport[sport] = bySport[sport].slice(-limit);
  }

  return bySport;
}

function isoWeekKey(date: Date): string {
  const utcDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNumber = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - dayNumber);

  const yearStart = new Date(Date.UTC(utcDate.getUTCFullYear(), 0, 1));
  const weekNumber = Math.ceil(((utcDate.getTime() - yearStart.getTime()) / 86_400_000 + 1) / 7);

  return `${utcDate.getUTCFullYear()}-W${String(weekNumber).padStart(2, "0")}`;
}
