import { cookies } from "next/headers";
import { SESSION_COOKIE_NAME } from "@/lib/auth";
import type { DateRange } from "@/lib/date-range";
import type { Activity, Objectif, Plan, Rapport, Seance } from "@/lib/types";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

// The frontend's own SSR fetches and Server Actions run server-to-server against the
// API — they don't go through the browser, so the session cookie isn't attached
// automatically the way it is for a client-side `fetch`. Forwarding it manually here
// is what lets the backend's `get_current_user` gate (ADR-0008) recognize the
// logged-in visitor. This assumes the cookie is visible to both origins (true on
// localhost regardless of port, since cookie scoping ignores port — see proxy.ts);
// a production deployment on separate registrable domains needs a shared cookie
// `Domain` instead.
async function authHeaders(): Promise<HeadersInit> {
  const session = (await cookies()).get(SESSION_COOKIE_NAME);
  return session ? { Cookie: `${SESSION_COOKIE_NAME}=${session.value}` } : {};
}

export async function fetchActivities(range?: DateRange): Promise<Activity[]> {
  const search = new URLSearchParams();
  if (range?.since) search.set("since", range.since);
  if (range?.until) search.set("until", range.until);
  const query = search.toString();

  const res = await fetch(`${API_URL}/activities${query ? `?${query}` : ""}`, {
    headers: await authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch activities: ${res.status}`);
  }
  return res.json();
}

export async function fetchActivity(garminActivityId: string): Promise<Activity | null> {
  const res = await fetch(`${API_URL}/activities/${garminActivityId}`, {
    headers: await authHeaders(),
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
    headers: await authHeaders(),
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to fetch rapport for activity ${garminActivityId}: ${res.status}`);
  }
  return res.json();
}

export async function fetchObjectif(): Promise<Objectif | null> {
  const res = await fetch(`${API_URL}/objectif`, { headers: await authHeaders(), cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to fetch the active objectif: ${res.status}`);
  }
  return res.json();
}

export async function fetchPlan(): Promise<Plan | null> {
  const res = await fetch(`${API_URL}/plan`, { headers: await authHeaders(), cache: "no-store" });
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
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
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
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(input),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to update seance ${seanceId}: ${res.status}`);
  }
  return res.json();
}

export type SetGeminiApiKeyResult = { success: true } | { success: false; error: string };

export async function setGeminiApiKey(apiKey: string): Promise<SetGeminiApiKeyResult> {
  const res = await fetch(`${API_URL}/users/me/gemini-key`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ api_key: apiKey }),
    cache: "no-store",
  });
  if (res.ok) return { success: true };

  const body: unknown = await res.json().catch(() => null);
  const detail =
    body && typeof body === "object" && "detail" in body ? String(body.detail) : undefined;
  return { success: false, error: detail ?? `Failed to save API key: ${res.status}` };
}
