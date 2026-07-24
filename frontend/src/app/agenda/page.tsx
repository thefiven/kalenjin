import Link from "next/link";
import { AgendaList } from "@/components/agenda-list";
import { Button } from "@/components/ui/button";
import { addWeeks, weekBounds } from "@/lib/date-range";
import { fetchActivities } from "@/lib/api";

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export default async function AgendaPage({
  searchParams,
}: {
  searchParams: Promise<{ week?: string }>;
}) {
  const { week } = await searchParams;
  const anchor = week ?? todayIsoDate();
  const { since, until } = weekBounds(anchor);
  const activities = await fetchActivities({ since, until });

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-4 text-xl font-semibold">Agenda</h1>
      <div className="mb-4 flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          nativeButton={false}
          render={<Link href={`/agenda?week=${addWeeks(since, -1)}`}>← Previous week</Link>}
        />
        <span className="text-sm text-muted-foreground">
          {since} – {until}
        </span>
        <Button
          variant="outline"
          size="sm"
          nativeButton={false}
          render={<Link href={`/agenda?week=${addWeeks(since, 1)}`}>Next week →</Link>}
        />
      </div>
      <AgendaList activities={activities} />
    </div>
  );
}
