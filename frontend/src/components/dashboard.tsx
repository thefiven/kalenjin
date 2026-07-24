import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDistance } from "@/lib/format";
import { groupBySport, weeklyDistance } from "@/lib/trends";
import type { Activity } from "@/lib/types";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h3>{title}</h3>
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

export function Dashboard({ activities }: { activities: Activity[] }) {
  const bySport = groupBySport(activities);
  const byWeek = weeklyDistance(activities);

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <Section title="Fitness trend">
        {byWeek.length === 0 ? (
          <Placeholder>No sessions yet.</Placeholder>
        ) : (
          <ul className="flex flex-col gap-1 text-sm">
            {byWeek.map((week) => (
              <li key={week.week} className="flex justify-between">
                <span className="text-muted-foreground">{week.week}</span>
                <span>{formatDistance(week.totalDistanceMeters)}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Progression by session type">
        {Object.keys(bySport).length === 0 ? (
          <Placeholder>No sessions yet.</Placeholder>
        ) : (
          <ul className="flex flex-col gap-1 text-sm">
            {Object.entries(bySport).map(([sport, summary]) => (
              <li key={sport} className="flex justify-between">
                <span>{sport}</span>
                <span className="text-muted-foreground">
                  {summary.count} sessions · {formatDistance(summary.totalDistanceMeters)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Recovery">
        <Placeholder>
          No recovery data yet — resting heart rate and HRV aren&apos;t synced yet.
        </Placeholder>
      </Section>

      <Section title="Plan adherence">
        <Placeholder>No training plan yet.</Placeholder>
      </Section>
    </div>
  );
}
