export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.round((totalSeconds % 3600) / 60);
  return hours > 0 ? `${hours}h${minutes.toString().padStart(2, "0")}` : `${minutes} min`;
}

export function formatDistance(meters: number | null): string {
  if (meters === null) return "—";
  return `${(meters / 1000).toFixed(2)} km`;
}
