from __future__ import annotations

from dataclasses import replace
from datetime import date

from kalenjin.llm.domain import LLMClient
from kalenjin.plan.completion import match_completed_seances
from kalenjin.plan.detailing import promote_due_weeks
from kalenjin.plan.domain import GarminPushClient, ObjectifRepository, PlanRepository
from kalenjin.plan.push import sync_plan_to_garmin
from kalenjin.sync.domain import ActivityRepository, ActivitySource
from kalenjin.sync.service import SyncResult, sync_activities


class SyncOrchestrator:
    """Owns the `/sync` workflow end to end (issues #6, #9, #10): ingest new
    activities, match them against the active Plan's séances, promote any week
    entering the detail horizon, then push never-pushed séances to Garmin.

    A no-op past ingestion when there's no active Objectif/Plan yet — Plan
    generation (issue #4) doesn't necessarily happen before the first sync.
    """

    def __init__(
        self,
        source: ActivitySource,
        activity_repo: ActivityRepository,
        objectif_repo: ObjectifRepository,
        plan_repo: PlanRepository,
        garmin: GarminPushClient,
        llm: LLMClient,
    ) -> None:
        self._source = source
        self._activity_repo = activity_repo
        self._objectif_repo = objectif_repo
        self._plan_repo = plan_repo
        self._garmin = garmin
        self._llm = llm

    def run(self, today: date) -> SyncResult:
        result = sync_activities(self._source, self._activity_repo, today=today)

        objectif = self._objectif_repo.get_active()
        plan = self._plan_repo.get_active()
        if objectif is None or plan is None:
            return result

        completions = match_completed_seances(
            plan.seances, self._activity_repo.list_activities(), today=today
        )
        if completions:
            self._plan_repo.update_seances(completions)
            plan = self._plan_repo.get_active()
            assert plan is not None

        promotion = promote_due_weeks(plan.seances, objectif, llm=self._llm, today=today)
        if promotion.new_seances:
            new_seances = [replace(s, plan_id=plan.id) for s in promotion.new_seances]
            self._plan_repo.replace_seances(promotion.removed_seance_ids, new_seances)
            plan = self._plan_repo.get_active()
            assert plan is not None

        # Only never-pushed here — an already-pushed séance is only re-pushed when the
        # Plan is actually adjusted (see RapportOrchestrator), not on every sync.
        never_pushed = [s for s in plan.seances if s.garmin_workout_id is None]
        sync_plan_to_garmin(
            never_pushed,
            sport=objectif.sport,
            client=self._garmin,
            plan_repo=self._plan_repo,
            today=today,
        )

        return result
