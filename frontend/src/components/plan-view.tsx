import { updateSeanceAction } from "@/app/plan/actions";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDistance } from "@/lib/format";
import type { Objectif, Seance, SeanceStatus } from "@/lib/types";

function statusVariant(status: SeanceStatus): "default" | "secondary" | "destructive" {
  if (status === "completed") return "default";
  if (status === "skipped") return "destructive";
  return "secondary";
}

function groupByWeek(seances: Seance[]): [string, Seance[]][] {
  const groups = new Map<string, Seance[]>();
  for (const seance of seances) {
    const list = groups.get(seance.week_start) ?? [];
    list.push(seance);
    groups.set(seance.week_start, list);
  }
  return Array.from(groups.entries()).sort(([a], [b]) => (a < b ? -1 : 1));
}

function DetailedSeanceRow({ seance }: { seance: Seance }) {
  return (
    <form
      action={updateSeanceAction.bind(null, seance.id)}
      className="flex flex-wrap items-center gap-2"
    >
      <span className="w-24 shrink-0 text-muted-foreground">{seance.scheduled_date}</span>
      <select
        name="seance_type"
        defaultValue={seance.seance_type ?? "easy"}
        className="rounded border bg-background px-1 py-0.5 text-xs"
      >
        <option value="easy">easy</option>
        <option value="long_run">long_run</option>
        <option value="tempo">tempo</option>
        <option value="interval">interval</option>
      </select>
      <input
        type="number"
        name="distance_meters"
        defaultValue={seance.distance_meters ?? 0}
        className="w-20 rounded border bg-background px-1 py-0.5 text-xs"
      />
      <span className="text-xs text-muted-foreground">
        {formatDistance(seance.distance_meters)}
      </span>
      <Badge variant={statusVariant(seance.status)}>{seance.status}</Badge>
      <button type="submit" className="text-xs underline">
        Save
      </button>
    </form>
  );
}

export function PlanView({ objectif, seances }: { objectif: Objectif; seances: Seance[] }) {
  const weeks = groupByWeek(seances);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Objectif</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">
            {objectif.sport} — {formatDistance(objectif.target_distance_meters)} by{" "}
            {objectif.target_date}
          </p>
        </CardContent>
      </Card>

      {weeks.map(([weekStart, weekSeances]) => (
        <Card key={weekStart}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span>{weekStart}</span>
              <Badge variant="secondary">{weekSeances[0].phase}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            {weekSeances[0].detail === "coarse" ? (
              <p className="text-muted-foreground">{weekSeances[0].theme}</p>
            ) : (
              weekSeances
                .slice()
                .sort((a, b) => ((a.scheduled_date ?? "") < (b.scheduled_date ?? "") ? -1 : 1))
                .map((seance) => <DetailedSeanceRow key={seance.id} seance={seance} />)
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
