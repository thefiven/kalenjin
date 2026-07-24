import { RapportPanel } from "@/components/rapport-panel";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatDate, formatDistance, formatDuration } from "@/lib/format";
import type { Activity, Rapport } from "@/lib/types";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

export function ActivityDetail({
  activity,
  rapport = null,
}: {
  activity: Activity;
  rapport?: Rapport | null;
}) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Badge variant="secondary">{activity.sport}</Badge>
            <span className="text-sm text-muted-foreground">
              {formatDate(activity.started_at)}
            </span>
          </CardTitle>
        </CardHeader>
        <Separator />
        <CardContent className="grid grid-cols-3 gap-4">
          <Metric label="Distance" value={formatDistance(activity.distance_meters)} />
          <Metric label="Duration" value={formatDuration(activity.duration_seconds)} />
          <Metric
            label="Avg. heart rate"
            value={
              activity.average_heart_rate === null
                ? "—"
                : `${Math.round(activity.average_heart_rate)} bpm`
            }
          />
        </CardContent>
      </Card>
      <RapportPanel rapport={rapport} />
    </div>
  );
}
