import { Dashboard } from "@/components/dashboard";
import { fetchActivities, fetchPlan } from "@/lib/api";

export default async function DashboardPage() {
  const [activities, plan] = await Promise.all([fetchActivities(), fetchPlan()]);

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-4 text-xl font-semibold">Dashboard</h1>
      <Dashboard activities={activities} planSeances={plan?.seances ?? null} />
    </div>
  );
}
