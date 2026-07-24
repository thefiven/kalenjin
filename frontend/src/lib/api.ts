import type { DateRange } from "@/lib/date-range";
import type { Activity, Objectif, Plan, Rapport, Seance } from "@/lib/types";

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

export async function fetchObjectif(): Promise<Objectif | null> {
  const res = await fetch(`${API_URL}/objectif`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to fetch the active objectif: ${res.status}`);
  }
  return res.json();
}

export async function fetchPlan(): Promise<Plan | null> {
  const res = await fetch(`${API_URL}/plan`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to fetch the active plan: ${res.status}`);
  }
  return res.json();
}

export interface CreateObjectifInput {
  sport: string;
  target_distance_meters: number;
  target_date: string;
  target_time_seconds?: number;
}

export async function createObjectif(input: CreateObjectifInput): Promise<Plan> {
  const res = await fetch(`${API_URL}/objectif`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to create objectif: ${res.status}`);
  }
  return res.json();
}

export interface UpdateSeanceInput {
  seance_type?: string;
  distance_meters?: number;
  status?: string;
}

export async function updateSeance(seanceId: number, input: UpdateSeanceInput): Promise<Seance> {
  const res = await fetch(`${API_URL}/plan/seances/${seanceId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to update seance ${seanceId}: ${res.status}`);
  }
  return res.json();
}
