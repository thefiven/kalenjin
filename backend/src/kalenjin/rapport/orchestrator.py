from __future__ import annotations

from datetime import date

from kalenjin.llm.domain import LLMClient
from kalenjin.plan.adjustment import adjust_plan_for_rapport
from kalenjin.plan.domain import GarminPushClient, ObjectifRepository, PlanRepository
from kalenjin.plan.push import sync_plan_to_garmin
from kalenjin.rapport.domain import RapportRecord, RapportRepository
from kalenjin.rapport.service import generate_rapport, select_history
from kalenjin.sync.domain import ActivityRepository


class RapportOrchestrator:
    """Owns the post-séance Rapport workflow end to end (issues #8, #9, #10):
    generate the AI Rapport for a completed activity, persist it, then adjust and
    re-push the Plan if the Rapport's flag/effort warrants it.

    Returns `None` when `garmin_activity_id` doesn't match a known activity — the
    caller (an HTTP route) turns that into its own 404; this module stays
    transport-agnostic.
    """

    def __init__(
        self,
        activity_repo: ActivityRepository,
        rapport_repo: RapportRepository,
        objectif_repo: ObjectifRepository,
        plan_repo: PlanRepository,
        garmin: GarminPushClient,
        llm: LLMClient,
        recent_rapports_for_adjustment: int,
    ) -> None:
        self._activity_repo = activity_repo
        self._rapport_repo = rapport_repo
        self._objectif_repo = objectif_repo
        self._plan_repo = plan_repo
        self._garmin = garmin
        self._llm = llm
        self._recent_rapports_for_adjustment = recent_rapports_for_adjustment

    def generate_for_activity(self, garmin_activity_id: str, today: date) -> RapportRecord | None:
        activity = self._activity_repo.get_activity(garmin_activity_id)
        if activity is None:
            return None

        history = select_history(activity, self._activity_repo.list_activities())
        rapport = generate_rapport(activity, history=history, llm=self._llm)
        recent_rapports = self._rapport_repo.list_recent(self._recent_rapports_for_adjustment)
        self._rapport_repo.save(rapport)

        plan = self._plan_repo.get_active()
        objectif = self._objectif_repo.get_active()
        if plan is not None and objectif is not None:
            adjusted = adjust_plan_for_rapport(
                plan.seances, rapport=rapport, recent_rapports=recent_rapports, today=today
            )
            if adjusted:
                self._plan_repo.update_seances(adjusted)
                sync_plan_to_garmin(
                    adjusted,
                    sport=objectif.sport,
                    client=self._garmin,
                    plan_repo=self._plan_repo,
                    today=today,
                )

        return rapport
