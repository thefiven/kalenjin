from datetime import date, datetime

from kalenjin.plan.adjustment import adjust_plan_for_rapport
from kalenjin.plan.domain import SeanceRecord
from kalenjin.rapport.domain import PerceivedEffort, RapportFlag, RapportRecord

TODAY = date(2026, 1, 12)


def _seance(
    id: int,
    scheduled_date: date | None,
    detail: str = "detailed",
    status: str = "pending",
    seance_type: str | None = "easy",
    distance_meters: float | None = 10_000,
    week_volume_meters: float = 20_000,
) -> SeanceRecord:
    return SeanceRecord(
        id=id,
        plan_id=1,
        week_start=date(2026, 1, 12),
        phase="build",
        detail=detail,  # type: ignore[arg-type]
        scheduled_date=scheduled_date,
        seance_type=seance_type,  # type: ignore[arg-type]
        distance_meters=distance_meters,
        theme=None if detail == "detailed" else "Build — ~20km target volume",
        week_volume_meters=week_volume_meters,
        status=status,  # type: ignore[arg-type]
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def _rapport(
    perceived_effort: PerceivedEffort = "as_expected",
    flag: RapportFlag = "none",
    completed_as_planned: bool = True,
) -> RapportRecord:
    return RapportRecord(
        garmin_activity_id="1",
        strengths="x",
        improvements="y",
        generated_at=datetime(2026, 1, 12, 8, 0),
        completed_as_planned=completed_as_planned,
        perceived_effort=perceived_effort,
        flag=flag,
    )


def test_no_adjustment_on_a_nominal_rapport() -> None:
    seances = [_seance(1, scheduled_date=date(2026, 1, 14))]

    adjusted = adjust_plan_for_rapport(seances, rapport=_rapport(), recent_rapports=[], today=TODAY)

    assert adjusted == []


def test_pain_flag_converts_the_soonest_upcoming_seance_to_an_easy_recovery_session() -> None:
    seances = [
        _seance(1, scheduled_date=date(2026, 1, 14), seance_type="tempo", distance_meters=8_000),
        _seance(2, scheduled_date=date(2026, 1, 16), seance_type="easy", distance_meters=6_000),
    ]

    adjusted = adjust_plan_for_rapport(
        seances, rapport=_rapport(flag="pain"), recent_rapports=[], today=TODAY
    )

    assert len(adjusted) == 1
    assert adjusted[0].id == 1
    assert adjusted[0].seance_type == "easy"
    assert (adjusted[0].distance_meters or 0) < 8_000


def test_illness_flag_also_triggers_the_hard_stop() -> None:
    seances = [_seance(1, scheduled_date=date(2026, 1, 14), seance_type="interval")]

    adjusted = adjust_plan_for_rapport(
        seances, rapport=_rapport(flag="illness"), recent_rapports=[], today=TODAY
    )

    assert len(adjusted) == 1
    assert adjusted[0].seance_type == "easy"


def test_hard_stop_never_touches_past_or_already_completed_seances() -> None:
    seances = [
        _seance(1, scheduled_date=date(2026, 1, 10), seance_type="tempo"),  # in the past
        _seance(2, scheduled_date=date(2026, 1, 14), status="completed"),
        _seance(3, scheduled_date=None, detail="coarse"),  # coarse, not yet detailed
        _seance(4, scheduled_date=date(2026, 1, 20), seance_type="tempo"),
    ]

    adjusted = adjust_plan_for_rapport(
        seances, rapport=_rapport(flag="pain"), recent_rapports=[], today=TODAY
    )

    assert [s.id for s in adjusted] == [4]


def test_single_high_effort_report_does_not_trigger_a_backoff() -> None:
    seances = [_seance(1, scheduled_date=date(2026, 1, 14), distance_meters=10_000)]

    adjusted = adjust_plan_for_rapport(
        seances, rapport=_rapport(perceived_effort="high"), recent_rapports=[], today=TODAY
    )

    assert adjusted == []


def test_two_consecutive_high_effort_reports_trigger_a_backoff_on_all_pending_seances() -> None:
    seances = [
        _seance(1, scheduled_date=date(2026, 1, 14), distance_meters=10_000),
        _seance(2, scheduled_date=date(2026, 1, 16), distance_meters=6_000),
    ]

    adjusted = adjust_plan_for_rapport(
        seances,
        rapport=_rapport(perceived_effort="high"),
        recent_rapports=[_rapport(perceived_effort="high")],
        today=TODAY,
    )

    assert {s.id for s in adjusted} == {1, 2}
    assert all((s.distance_meters or 0) < 10_000 or s.id == 2 for s in adjusted)


def test_backoff_only_reduces_it_never_increases_volume() -> None:
    seances = [_seance(1, scheduled_date=date(2026, 1, 14), distance_meters=10_000)]

    adjusted = adjust_plan_for_rapport(
        seances,
        rapport=_rapport(perceived_effort="high"),
        recent_rapports=[_rapport(perceived_effort="high")],
        today=TODAY,
    )

    assert adjusted[0].distance_meters is not None
    assert adjusted[0].distance_meters < 10_000


def test_backoff_is_capped_at_fifteen_percent_per_pass() -> None:
    seances = [_seance(1, scheduled_date=date(2026, 1, 14), distance_meters=10_000)]

    adjusted = adjust_plan_for_rapport(
        seances,
        rapport=_rapport(perceived_effort="high"),
        recent_rapports=[_rapport(perceived_effort="high")],
        today=TODAY,
    )

    assert adjusted[0].distance_meters == 10_000 * 0.85


def test_a_non_high_effort_report_resets_the_consecutive_streak() -> None:
    seances = [_seance(1, scheduled_date=date(2026, 1, 14), distance_meters=10_000)]

    adjusted = adjust_plan_for_rapport(
        seances,
        rapport=_rapport(perceived_effort="high"),
        recent_rapports=[
            _rapport(perceived_effort="as_expected"),
            _rapport(perceived_effort="high"),
        ],
        today=TODAY,
    )

    assert adjusted == []
