from datetime import date, datetime, timedelta
from typing import Any

from kalenjin.plan.domain import ObjectifRecord, PlanRecord, SeanceRecord
from kalenjin.sync.orchestrator import SyncOrchestrator
from support.fakes import (
    FakeGarminPushClient,
    FakeLLMClient,
    FakeObjectifRepository,
    FakePlanRepository,
    FakeRepository,
    raw_activity,
)

TODAY = date(2026, 1, 12)


class _AnyRangeSource:
    """Returns the same activities regardless of the requested date range — these
    tests care about orchestration (completion/promotion/push wiring), not the
    chunking/range logic already covered by `sync.test_service`."""

    def __init__(self, raw_activities: list[dict[str, Any]]) -> None:
        self._raw_activities = raw_activities

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        return self._raw_activities


def _objectif(target_date: date = TODAY + timedelta(weeks=8)) -> ObjectifRecord:
    return ObjectifRecord(
        id=1,
        sport="running",
        target_distance_meters=10_000,
        target_date=target_date,
        target_time_seconds=None,
        created_at=datetime(2026, 1, 1, 8, 0),
    )


def _detailed_seance(id: int, scheduled_date: date | None, status: str = "pending") -> SeanceRecord:
    return SeanceRecord(
        id=id,
        plan_id=1,
        week_start=date(2026, 1, 5),
        phase="base",
        detail="detailed",
        scheduled_date=scheduled_date,
        seance_type="easy",
        distance_meters=5000.0,
        theme=None,
        week_volume_meters=20_000,
        status=status,
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def _orchestrator(
    activity_repo: FakeRepository,
    objectif_repo: FakeObjectifRepository,
    plan_repo: FakePlanRepository,
    garmin: FakeGarminPushClient,
    raw_activities: list[dict[str, Any]] | None = None,
) -> SyncOrchestrator:
    return SyncOrchestrator(
        source=_AnyRangeSource(raw_activities or []),
        activity_repo=activity_repo,
        objectif_repo=objectif_repo,
        plan_repo=plan_repo,
        garmin=garmin,
        llm=FakeLLMClient("[]"),
    )


def test_reports_imported_count_with_no_active_objectif_or_plan() -> None:
    orchestrator = _orchestrator(
        FakeRepository(),
        FakeObjectifRepository(),
        FakePlanRepository(),
        FakeGarminPushClient(),
        raw_activities=[raw_activity("1")],
    )

    result = orchestrator.run(today=TODAY)

    assert result.imported_count == 1


def test_marks_a_past_due_seance_completed_against_a_synced_activity() -> None:
    past_scheduled = TODAY - timedelta(days=1)
    activity_repo = FakeRepository()
    objectif_repo = FakeObjectifRepository(existing=[_objectif()])
    plan_repo = FakePlanRepository(
        existing=PlanRecord(
            id=1,
            objectif_id=1,
            created_at=datetime(2026, 1, 1, 8, 0),
            seances=[_detailed_seance(1, past_scheduled)],
        )
    )
    raw = raw_activity("a1", started_at=f"{past_scheduled.isoformat()} 00:00:00")
    orchestrator = _orchestrator(
        activity_repo, objectif_repo, plan_repo, FakeGarminPushClient(), raw_activities=[raw]
    )

    orchestrator.run(today=TODAY)

    updated = plan_repo.get_active().seances[0]  # type: ignore[union-attr]
    assert updated.status == "completed"
    assert updated.garmin_activity_id == "a1"


def test_pushes_a_never_pushed_upcoming_seance() -> None:
    objectif_repo = FakeObjectifRepository(existing=[_objectif()])
    plan_repo = FakePlanRepository(
        existing=PlanRecord(
            id=1,
            objectif_id=1,
            created_at=datetime(2026, 1, 1, 8, 0),
            seances=[_detailed_seance(1, TODAY + timedelta(days=2))],
        )
    )
    garmin = FakeGarminPushClient()
    orchestrator = _orchestrator(FakeRepository(), objectif_repo, plan_repo, garmin)

    orchestrator.run(today=TODAY)

    assert len(garmin.pushed) == 1
    assert plan_repo.get_active().seances[0].garmin_workout_id == "workout-1"  # type: ignore[union-attr]
