import type { Seance } from "@/lib/types";

export interface AdherenceSummary {
  completedCount: number;
  totalCount: number;
  ratio: number;
}

export function planAdherence(seances: Seance[]): AdherenceSummary | null {
  const resolved = seances.filter(
    (s) => s.detail === "detailed" && (s.status === "completed" || s.status === "skipped"),
  );
  if (resolved.length === 0) return null;

  const completedCount = resolved.filter((s) => s.status === "completed").length;
  return {
    completedCount,
    totalCount: resolved.length,
    ratio: completedCount / resolved.length,
  };
}
