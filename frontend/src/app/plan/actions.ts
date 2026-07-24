"use server";

import { revalidatePath } from "next/cache";
import { createObjectif, updateSeance } from "@/lib/api";

function parseTargetTimeSeconds(value: FormDataEntryValue | null): number | undefined {
  if (!value) return undefined;
  const [hours, minutes, seconds] = String(value).split(":").map(Number);
  return hours * 3600 + minutes * 60 + (seconds ?? 0);
}

export async function createObjectifAction(formData: FormData): Promise<void> {
  const sport = String(formData.get("sport") ?? "running");
  const targetDistanceMeters = Number(formData.get("target_distance_meters"));
  const targetDate = String(formData.get("target_date"));
  const targetTimeSeconds = parseTargetTimeSeconds(formData.get("target_time"));

  await createObjectif({
    sport,
    target_distance_meters: targetDistanceMeters,
    target_date: targetDate,
    target_time_seconds: targetTimeSeconds,
  });

  revalidatePath("/plan");
  revalidatePath("/dashboard");
}

export async function updateSeanceAction(seanceId: number, formData: FormData): Promise<void> {
  const seanceType = formData.get("seance_type");
  const distanceMeters = formData.get("distance_meters");

  await updateSeance(seanceId, {
    seance_type: seanceType ? String(seanceType) : undefined,
    distance_meters: distanceMeters ? Number(distanceMeters) : undefined,
  });

  revalidatePath("/plan");
}
