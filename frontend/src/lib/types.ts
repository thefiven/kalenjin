export interface Activity {
  garmin_activity_id: string;
  sport: string;
  started_at: string;
  duration_seconds: number;
  distance_meters: number | null;
  average_heart_rate: number | null;
}

export interface Rapport {
  garmin_activity_id: string;
  strengths: string;
  improvements: string;
  generated_at: string;
}

export interface Objectif {
  id: number;
  sport: string;
  target_distance_meters: number;
  target_date: string;
  target_time_seconds: number | null;
}

export type SeanceDetail = "coarse" | "detailed";
export type SeanceType = "easy" | "long_run" | "tempo" | "interval";
export type SeanceStatus = "pending" | "completed" | "skipped";

export interface Seance {
  id: number;
  week_start: string;
  phase: string;
  detail: SeanceDetail;
  scheduled_date: string | null;
  seance_type: SeanceType | null;
  distance_meters: number | null;
  theme: string | null;
  week_volume_meters: number;
  status: SeanceStatus;
  garmin_activity_id: string | null;
}

export interface Plan {
  id: number;
  objectif_id: number;
  seances: Seance[];
}
