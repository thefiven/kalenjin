export interface DateRange {
  since?: string;
  until?: string;
}

const ISO_DATE = "T00:00:00Z";

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function weekBounds(isoDate: string): { since: string; until: string } {
  const date = new Date(`${isoDate}${ISO_DATE}`);
  const dayOfWeek = date.getUTCDay() || 7; // Monday=1 ... Sunday=7

  const monday = new Date(date);
  monday.setUTCDate(date.getUTCDate() - (dayOfWeek - 1));

  const sunday = new Date(monday);
  sunday.setUTCDate(monday.getUTCDate() + 6);

  return { since: toIsoDate(monday), until: toIsoDate(sunday) };
}

export function addWeeks(isoDate: string, weeks: number): string {
  const date = new Date(`${isoDate}${ISO_DATE}`);
  date.setUTCDate(date.getUTCDate() + weeks * 7);
  return toIsoDate(date);
}
