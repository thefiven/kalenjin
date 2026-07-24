import type { Activity } from "@/lib/types";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function fetchActivities(params?: {
  since?: string;
  until?: string;
}): Promise<Activity[]> {
  const search = new URLSearchParams();
  if (params?.since) search.set("since", params.since);
  if (params?.until) search.set("until", params.until);
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
