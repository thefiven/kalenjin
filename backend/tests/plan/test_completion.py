from datetime import date, datetime

from kalenjin.plan.completion import match_completed_seances
from kalenjin.plan.domain import SeanceRecord
from kalenjin.sync.domain import ActivityRecord

TODAY = date(2026, 1, 12)


def _seance(id: int, scheduled_date: date, status: str = "pending") -> SeanceRecord:
    return SeanceRecord(
        id=id,
        plan_id=1,
        week_start=date(2026, 1, 5),
        phase="base",
        detail="detailed",
        scheduled_date=scheduled_date,
        seance_type="easy",
        distance_meters=5000,
        theme=None,
        week_volume_meters=20_000,
        status=status,
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def _activity(activity_id: str, started_at: date) -> ActivityRecord:
    return ActivityRecord(
        garmin_activity_id=activity_id,
        sport="running",
        started_at=datetime.combine(started_at, datetime.min.time()),
        duration_seconds=1800.0,
        distance_meters=5000.0,
        average_heart_rate=150.0,
        raw_payload={},
    )


def test_marks_a_past_due_seance_completed_when_an_activity_matches_its_date() -> None:
    seances = [_seance(1, scheduled_date=date(2026, 1, 10))]
    activities = [_activity("a1", date(2026, 1, 10))]

    updated = match_completed_seances(seances, activities, today=TODAY)

    assert len(updated) == 1
    assert updated[0].status == "completed"
    assert updated[0].garmin_activity_id == "a1"


def test_marks_a_past_due_seance_skipped_when_no_activity_matches() -> None:
    seances = [_seance(1, scheduled_date=date(2026, 1, 10))]

    updated = match_completed_seances(seances, [], today=TODAY)

    assert len(updated) == 1
    assert updated[0].status == "skipped"


def test_leaves_future_seances_untouched() -> None:
    seances = [_seance(1, scheduled_date=date(2026, 1, 20))]

    updated = match_completed_seances(seances, [], today=TODAY)

    assert updated == []


def test_leaves_already_completed_or_skipped_seances_untouched() -> None:
    seances = [
        _seance(1, scheduled_date=date(2026, 1, 10), status="completed"),
        _seance(2, scheduled_date=date(2026, 1, 10), status="skipped"),
    ]

    updated = match_completed_seances(seances, [], today=TODAY)

    assert updated == []


def test_ignores_coarse_seances() -> None:
    coarse = SeanceRecord(
        id=1,
        plan_id=1,
        week_start=date(2026, 1, 5),
        phase="base",
        detail="coarse",
        scheduled_date=None,
        seance_type=None,
        distance_meters=None,
        theme="Base — ~20km target volume",
        week_volume_meters=20_000,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )

    updated = match_completed_seances([coarse], [], today=TODAY)

    assert updated == []
