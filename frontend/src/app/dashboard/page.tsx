import { Dashboard } from "@/components/dashboard";
import { fetchActivities } from "@/lib/api";

export default async function DashboardPage() {
  const activities = await fetchActivities();

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-4 text-xl font-semibold">Dashboard</h1>
      <Dashboard activities={activities} />
    </div>
  );
}
