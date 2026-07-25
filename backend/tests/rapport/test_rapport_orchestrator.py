from datetime import date, datetime, timedelta

from kalenjin.plan.domain import ObjectifRecord, PlanRecord, SeanceRecord
from kalenjin.rapport.orchestrator import RapportOrchestrator
from kalenjin.sync.domain import ActivityRecord
from support.fakes import (
    FakeGarminPushClient,
    FakeLLMClient,
    FakeObjectifRepository,
    FakePlanRepository,
    FakeRapportRepository,
    FakeRepository,
)

RECENT_RAPPORTS_FOR_ADJUSTMENT = 5


def _activity(activity_id: str, started_at: datetime) -> ActivityRecord:
    return ActivityRecord(
        garmin_activity_id=activity_id,
        sport="running",
        started_at=started_at,
        duration_seconds=1800.0,
        distance_meters=5000.0,
        average_heart_rate=150.0,
        raw_payload={},
    )


def _objectif(target_date: date) -> ObjectifRecord:
    return ObjectifRecord(
        id=1,
        sport="running",
        target_distance_meters=10_000,
        target_date=target_date,
        target_time_seconds=None,
        created_at=datetime(2026, 1, 1, 8, 0),
    )


def _detailed_seance(id: int, scheduled_date: date, distance_meters: float = 8000) -> SeanceRecord:
    return SeanceRecord(
        id=id,
        plan_id=1,
        week_start=date(2026, 1, 5),
        phase="base",
        detail="detailed",
        scheduled_date=scheduled_date,
        seance_type="tempo",
        distance_meters=distance_meters,
        theme=None,
        week_volume_meters=20_000,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def _orchestrator(
    activity_repo: FakeRepository,
    rapport_repo: FakeRapportRepository,
    objectif_repo: FakeObjectifRepository,
    plan_repo: FakePlanRepository,
    garmin: FakeGarminPushClient,
    llm: FakeLLMClient,
) -> RapportOrchestrator:
    return RapportOrchestrator(
        activity_repo=activity_repo,
        rapport_repo=rapport_repo,
        objectif_repo=objectif_repo,
        plan_repo=plan_repo,
        garmin=garmin,
        llm=llm,
        recent_rapports_for_adjustment=RECENT_RAPPORTS_FOR_ADJUSTMENT,
    )


def test_returns_none_when_activity_is_missing() -> None:
    orchestrator = _orchestrator(
        FakeRepository(),
        FakeRapportRepository(),
        FakeObjectifRepository(),
        FakePlanRepository(),
        FakeGarminPushClient(),
        FakeLLMClient('{"strengths": "x", "improvements": "y"}'),
    )

    rapport = orchestrator.generate_for_activity("does-not-exist", today=date(2026, 1, 12))

    assert rapport is None


def test_generates_and_persists_a_rapport_with_no_active_plan() -> None:
    activity_repo = FakeRepository(existing=[_activity("1", datetime(2026, 1, 5, 7, 0))])
    rapport_repo = FakeRapportRepository()
    llm = FakeLLMClient(
        '{"strengths": "Good pace.", "improvements": "Add strides.", '
        '"completed_as_planned": true, "perceived_effort": "as_expected", "flag": "none"}'
    )
    orchestrator = _orchestrator(
        activity_repo,
        rapport_repo,
        FakeObjectifRepository(),
        FakePlanRepository(),
        FakeGarminPushClient(),
        llm,
    )

    rapport = orchestrator.generate_for_activity("1", today=date(2026, 1, 12))

    assert rapport is not None
    assert rapport.strengths == "Good pace."
    assert rapport_repo.get_for_activity("1") is not None


def test_a_pain_flag_adjusts_and_re_pushes_the_upcoming_plan() -> None:
    activity_repo = FakeRepository(existing=[_activity("1", datetime(2026, 1, 5, 7, 0))])
    rapport_repo = FakeRapportRepository()
    objectif_repo = FakeObjectifRepository(existing=[_objectif(date(2026, 6, 1))])
    plan_repo = FakePlanRepository(
        existing=PlanRecord(
            id=1,
            objectif_id=1,
            created_at=datetime(2026, 1, 1, 8, 0),
            seances=[_detailed_seance(1, date.today() + timedelta(days=2))],
        )
    )
    llm = FakeLLMClient(
        '{"strengths": "x", "improvements": "y", "completed_as_planned": false, '
        '"perceived_effort": "high", "flag": "pain"}'
    )
    garmin = FakeGarminPushClient()
    orchestrator = _orchestrator(activity_repo, rapport_repo, objectif_repo, plan_repo, garmin, llm)

    orchestrator.generate_for_activity("1", today=date.today())

    updated = plan_repo.get_active().seances[0]  # type: ignore[union-attr]
    assert updated.seance_type == "easy"
    assert (updated.distance_meters or 0) < 8000
    assert len(garmin.pushed) == 1
    assert updated.garmin_workout_id == "workout-1"
