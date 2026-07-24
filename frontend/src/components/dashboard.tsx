import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { planAdherence } from "@/lib/adherence";
import { formatDistance, formatPace } from "@/lib/format";
import { groupBySport, recentPaceBySport, weeklyDistance } from "@/lib/trends";
import type { Activity, Seance } from "@/lib/types";

const RECENT_SESSIONS_PER_SPORT = 5;

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h3>{title}</h3>
        </CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

export function Dashboard({
  activities,
  planSeances = null,
}: {
  activities: Activity[];
  planSeances?: Seance[] | null;
}) {
  const bySport = groupBySport(activities);
  const byWeek = weeklyDistance(activities);
  const recentPace = recentPaceBySport(activities, RECENT_SESSIONS_PER_SPORT);
  const adherence = planSeances === null ? null : planAdherence(planSeances);

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <Section
        title="Fitness trend"
        description="Weekly distance — VO2max, critical pace, and training load aren't tracked yet."
      >
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

      <Section
        title="Progression by session type"
        description={`Pace on the last ${RECENT_SESSIONS_PER_SPORT} sessions, oldest first, per sport.`}
      >
        {Object.keys(bySport).length === 0 ? (
          <Placeholder>No sessions yet.</Placeholder>
        ) : (
          <ul className="flex flex-col gap-3 text-sm">
            {Object.entries(bySport).map(([sport, summary]) => (
              <li key={sport} className="flex flex-col gap-1">
                <div className="flex justify-between">
                  <span className="font-medium">{sport}</span>
                  <span className="text-muted-foreground">
                    {summary.count} sessions · {formatDistance(summary.totalDistanceMeters)}
                  </span>
                </div>
                {recentPace[sport] ? (
                  <div className="flex gap-3 text-xs text-muted-foreground">
                    {recentPace[sport].map((point) => (
                      <span key={point.startedAt}>{formatPace(point.paceSecondsPerKm)}</span>
                    ))}
                  </div>
                ) : null}
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
        {planSeances === null ? (
          <Placeholder>No training plan yet.</Placeholder>
        ) : adherence === null ? (
          <Placeholder>No planned session is due yet.</Placeholder>
        ) : (
          <p className="text-sm">
            {adherence.completedCount}/{adherence.totalCount} planned sessions completed (
            {Math.round(adherence.ratio * 100)}%)
          </p>
        )}
      </Section>
    </div>
  );
}
