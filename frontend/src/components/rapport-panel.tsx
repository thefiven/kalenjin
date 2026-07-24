import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Rapport } from "@/lib/types";

function Placeholder({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

export function RapportPanel({ rapport }: { rapport: Rapport | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Rapport</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {rapport === null ? (
          <Placeholder>No rapport has been generated for this session yet.</Placeholder>
        ) : (
          <>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">What went well</span>
              <p className="text-sm">{rapport.strengths}</p>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">Areas for improvement</span>
              <p className="text-sm">{rapport.improvements}</p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
