from datetime import date, datetime, timedelta

import pytest

from kalenjin.plan.domain import PlanRecord, SeanceRecord
from kalenjin.plan.push import sync_plan_to_garmin
from support.fakes import FakeGarminPushClient, FakePlanRepository

TODAY = date(2026, 1, 12)


def _sync(
    seances: list[SeanceRecord],
    client: FakeGarminPushClient,
    plan_repo: FakePlanRepository | None = None,
) -> list[SeanceRecord]:
    return sync_plan_to_garmin(
        seances,
        sport="running",
        client=client,
        plan_repo=plan_repo if plan_repo is not None else FakePlanRepository(),
        today=TODAY,
    )


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

    updated = _sync(seances, client)

    assert len(updated) == 1
    assert updated[0].id == 1
    assert updated[0].garmin_workout_id == "workout-1"
    assert len(client.pushed) == 1
    assert client.pushed[0][1] == "running"
    assert client.deleted == []


def test_does_not_push_coarse_seances() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, detail="coarse", scheduled_date=None)]

    updated = _sync(seances, client)

    assert updated == []
    assert client.pushed == []


def test_does_not_push_completed_or_skipped_seances() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, status="completed"), _seance(2, status="skipped")]

    updated = _sync(seances, client)

    assert updated == []
    assert client.pushed == []


def test_does_not_push_past_scheduled_seances() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, scheduled_date=TODAY - timedelta(days=1))]

    updated = _sync(seances, client)

    assert updated == []
    assert client.pushed == []


def test_pushes_a_seance_scheduled_for_today() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, scheduled_date=TODAY)]

    updated = _sync(seances, client)

    assert len(updated) == 1


def test_an_already_pushed_seance_is_deleted_then_recreated_not_duplicated() -> None:
    client = FakeGarminPushClient()
    seances = [_seance(1, garmin_workout_id="old-workout")]

    updated = _sync(seances, client)

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

    updated = _sync(seances, client)

    assert [s.id for s in updated] == [1]


def _plan_with(seances: list[SeanceRecord]) -> PlanRecord:
    return PlanRecord(id=1, objectif_id=1, created_at=datetime(2026, 1, 1), seances=seances)


def test_each_successful_push_is_committed_immediately() -> None:
    # A real, session-backed repository only durably persists on `commit()` — a plain
    # `update_seances` alone just stages the write in the ambient request transaction,
    # which gets rolled back wholesale if a later item in the same batch fails. So the
    # regression this guards against is push.py forgetting to call `commit()` per item,
    # not just calling `update_seances`.
    plan_repo = FakePlanRepository(existing=_plan_with([_seance(1), _seance(2)]))
    client = FakeGarminPushClient()

    _sync([_seance(1), _seance(2)], client, plan_repo)

    assert len(plan_repo.commit_snapshots) == 2
    last_commit = plan_repo.commit_snapshots[-1]
    assert [s.garmin_workout_id for s in last_commit.seances] == ["workout-1", "workout-2"]


def test_a_mid_batch_failure_commits_only_the_successes_before_it() -> None:
    plan_repo = FakePlanRepository(existing=_plan_with([_seance(1), _seance(2), _seance(3)]))
    client = FakeGarminPushClient(fail_at_push_number=2)

    with pytest.raises(RuntimeError):
        _sync([_seance(1), _seance(2), _seance(3)], client, plan_repo)

    # Only séance 1's push committed before the failure on séance 2 — that's the
    # durable state a fresh request would see, regardless of what update_seances did
    # to this fake's immediately-mutated working state.
    assert len(plan_repo.commit_snapshots) == 1
    by_id = {s.id: s.garmin_workout_id for s in plan_repo.commit_snapshots[0].seances}
    assert by_id[1] == "workout-1"
    assert by_id[2] is None
    assert by_id[3] is None
