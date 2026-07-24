import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate, formatDistance, formatDuration } from "@/lib/format";
import type { Activity } from "@/lib/types";

export function AgendaList({ activities }: { activities: Activity[] }) {
  if (activities.length === 0) {
    return <p className="text-sm text-muted-foreground">No sessions yet.</p>;
  }

  return (
    <ul className="flex flex-col gap-3">
      {activities.map((activity) => (
        <li key={activity.garmin_activity_id}>
          <Link href={`/agenda/${activity.garmin_activity_id}`}>
            <Card>
              <CardContent className="flex items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <span className="text-sm text-muted-foreground">
                    {formatDate(activity.started_at)}
                  </span>
                  <Badge variant="secondary">{activity.sport}</Badge>
                </div>
                <div className="flex flex-col items-end gap-1 text-sm">
                  <span>{formatDistance(activity.distance_meters)}</span>
                  <span>{formatDuration(activity.duration_seconds)}</span>
                </div>
              </CardContent>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}
