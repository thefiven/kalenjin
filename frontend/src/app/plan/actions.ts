"use server";

import { revalidatePath } from "next/cache";
import { createObjectif, updateSeance } from "@/lib/api";

export async function createObjectifAction(formData: FormData): Promise<void> {
  const sport = String(formData.get("sport") ?? "running");
  const targetDistanceMeters = Number(formData.get("target_distance_meters"));
  const targetDate = String(formData.get("target_date"));

  await createObjectif({
    sport,
    target_distance_meters: targetDistanceMeters,
    target_date: targetDate,
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
