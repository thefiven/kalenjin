import { ObjectifForm } from "@/components/objectif-form";
import { PlanView } from "@/components/plan-view";
import { fetchObjectif, fetchPlan } from "@/lib/api";

export default async function PlanPage() {
  const objectif = await fetchObjectif();
  const plan = objectif ? await fetchPlan() : null;

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-4 text-xl font-semibold">Plan</h1>
      {objectif === null || plan === null ? (
        <ObjectifForm />
      ) : (
        <PlanView objectif={objectif} seances={plan.seances} />
      )}
    </div>
  );
}
