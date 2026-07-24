import { createObjectifAction } from "@/app/plan/actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ObjectifForm() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Set a training goal</CardTitle>
        <CardDescription>
          Creates a Plan built around this Objectif — near-term sessions detailed, far-term
          weeks coarse-grained until they approach (see ADR-0001).
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form action={createObjectifAction} className="flex flex-col gap-3 text-sm">
          <label className="flex flex-col gap-1">
            Sport
            <select
              name="sport"
              defaultValue="running"
              className="rounded border bg-background px-2 py-1"
            >
              <option value="running">running</option>
              <option value="cycling">cycling</option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            Target distance (meters)
            <input
              type="number"
              name="target_distance_meters"
              required
              min={1}
              defaultValue={10000}
              className="rounded border bg-background px-2 py-1"
            />
          </label>
          <label className="flex flex-col gap-1">
            Target date
            <input
              type="date"
              name="target_date"
              required
              className="rounded border bg-background px-2 py-1"
            />
          </label>
          <label className="flex flex-col gap-1">
            Target level (finish time, optional)
            <input
              type="time"
              step={1}
              name="target_time"
              className="rounded border bg-background px-2 py-1"
            />
          </label>
          <Button type="submit" className="self-start">
            Create plan
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
