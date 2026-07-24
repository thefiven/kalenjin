import { AgendaList } from "@/components/agenda-list";
import { fetchActivities } from "@/lib/api";

export default async function AgendaPage() {
  const activities = await fetchActivities();

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-4 text-xl font-semibold">Agenda</h1>
      <AgendaList activities={activities} />
    </div>
  );
}
