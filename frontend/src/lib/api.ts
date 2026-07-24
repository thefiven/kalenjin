import type { DateRange } from "@/lib/date-range";
import type { Activity, Rapport } from "@/lib/types";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function fetchActivities(range?: DateRange): Promise<Activity[]> {
  const search = new URLSearchParams();
  if (range?.since) search.set("since", range.since);
  if (range?.until) search.set("until", range.until);
  const query = search.toString();

  const res = await fetch(`${API_URL}/activities${query ? `?${query}` : ""}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch activities: ${res.status}`);
  }
  return res.json();
}

export async function fetchActivity(garminActivityId: string): Promise<Activity | null> {
  const res = await fetch(`${API_URL}/activities/${garminActivityId}`, {
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to fetch activity ${garminActivityId}: ${res.status}`);
  }
  return res.json();
}

export async function fetchRapport(garminActivityId: string): Promise<Rapport | null> {
  const res = await fetch(`${API_URL}/activities/${garminActivityId}/rapport`, {
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to fetch rapport for activity ${garminActivityId}: ${res.status}`);
  }
  return res.json();
}
