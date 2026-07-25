from datetime import date, timedelta

from kalenjin.plan.domain import SeanceRecord, is_past_due_seance, is_upcoming_seance

TODAY = date(2026, 1, 12)


def _seance(
    detail: str = "detailed",
    status: str = "pending",
    scheduled_date: date | None = TODAY,
) -> SeanceRecord:
    return SeanceRecord(
        id=1,
        plan_id=1,
        week_start=date(2026, 1, 12),
        phase="base",
        detail=detail,  # type: ignore[arg-type]
        scheduled_date=scheduled_date,
        seance_type="easy" if detail == "detailed" else None,
        distance_meters=5000.0 if detail == "detailed" else None,
        theme=None if detail == "detailed" else "Base — ~20km target volume",
        week_volume_meters=20_000,
        status=status,  # type: ignore[arg-type]
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def test_is_upcoming_seance_true_for_a_detailed_pending_seance_scheduled_today_or_later() -> None:
    assert is_upcoming_seance(_seance(scheduled_date=TODAY), today=TODAY)
    assert is_upcoming_seance(_seance(scheduled_date=TODAY + timedelta(days=1)), today=TODAY)


def test_is_upcoming_seance_false_for_a_seance_scheduled_in_the_past() -> None:
    assert not is_upcoming_seance(_seance(scheduled_date=TODAY - timedelta(days=1)), today=TODAY)


def test_is_upcoming_seance_false_for_a_coarse_seance() -> None:
    assert not is_upcoming_seance(_seance(detail="coarse", scheduled_date=None), today=TODAY)


def test_is_upcoming_seance_false_for_a_completed_or_skipped_seance() -> None:
    assert not is_upcoming_seance(_seance(status="completed"), today=TODAY)
    assert not is_upcoming_seance(_seance(status="skipped"), today=TODAY)


def test_is_past_due_seance_true_for_a_detailed_pending_seance_scheduled_before_today() -> None:
    assert is_past_due_seance(_seance(scheduled_date=TODAY - timedelta(days=1)), today=TODAY)


def test_is_past_due_seance_false_for_a_seance_scheduled_today_or_later() -> None:
    assert not is_past_due_seance(_seance(scheduled_date=TODAY), today=TODAY)
    assert not is_past_due_seance(_seance(scheduled_date=TODAY + timedelta(days=1)), today=TODAY)


def test_is_past_due_seance_false_for_a_coarse_or_non_pending_seance() -> None:
    past = TODAY - timedelta(days=1)
    assert not is_past_due_seance(_seance(detail="coarse", scheduled_date=None), today=TODAY)
    assert not is_past_due_seance(_seance(status="completed", scheduled_date=past), today=TODAY)
