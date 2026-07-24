import { notFound } from "next/navigation";
import { ActivityDetail } from "@/components/activity-detail";
import { fetchActivity } from "@/lib/api";

export default async function ActivityDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const activity = await fetchActivity(id);

  if (!activity) {
    notFound();
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <ActivityDetail activity={activity} />
    </div>
  );
}
