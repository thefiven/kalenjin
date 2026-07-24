from datetime import date, timedelta

from kalenjin.plan.domain import SeanceRecord
from kalenjin.plan.push import sync_plan_to_garmin
from support.fakes import FakeGarminPushClient

TODAY = date(2026, 1, 12)


def _seance(
    id: int,
    detail: str = "detailed",
    status: str = "pending",
    scheduled_date: date | None = date(2026, 1, 14),
    garmin_workout_id: str | None = None,
) -> SeanceRecord:
    return SeanceRecord(
        id=id,
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
        garmin_workout_id=garmin_workout_id,
    )


def test_pushes_a_never_pushed_detailed_pending_upcoming_seance() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1)]

    updated = sync_plan_to_garmin(seances, sport="running", client=client, today=TODAY)

    assert len(updated) == 1
    assert updated[0].id == 1
    assert updated[0].garmin_workout_id == "workout-1"
    assert len(client.pushed) == 1
    assert client.pushed[0][1] == "running"
    assert client.deleted == []


def test_does_not_push_coarse_seances() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, detail="coarse", scheduled_date=None)]

    updated = sync_plan_to_garmin(seances, sport="running", client=client, today=TODAY)

    assert updated == []
    assert client.pushed == []


def test_does_not_push_completed_or_skipped_seances() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, status="completed"), _seance(2, status="skipped")]

    updated = sync_plan_to_garmin(seances, sport="running", client=client, today=TODAY)

    assert updated == []
    assert client.pushed == []


def test_does_not_push_past_scheduled_seances() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, scheduled_date=TODAY - timedelta(days=1))]

    updated = sync_plan_to_garmin(seances, sport="running", client=client, today=TODAY)

    assert updated == []
    assert client.pushed == []


def test_pushes_a_seance_scheduled_for_today() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, scheduled_date=TODAY)]

    updated = sync_plan_to_garmin(seances, sport="running", client=client, today=TODAY)

    assert len(updated) == 1


def test_an_already_pushed_seance_is_deleted_then_recreated_not_duplicated() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, garmin_workout_id="old-workout")]

    updated = sync_plan_to_garmin(seances, sport="running", client=client, today=TODAY)

    assert client.deleted == ["old-workout"]
    assert len(client.pushed) == 1
    assert updated[0].garmin_workout_id == "workout-1"


def test_only_pushed_seances_are_returned() -> None:
    client = FakeGarminPushClient()
    seances = [
        _seance(1),
        _seance(2, detail="coarse", scheduled_date=None),
        _seance(3, status="completed"),
    ]

    updated = sync_plan_to_garmin(seances, sport="running", client=client, today=TODAY)

    assert [s.id for s in updated] == [1]
