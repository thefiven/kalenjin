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
