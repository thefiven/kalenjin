import json
from datetime import date, datetime, timedelta

from kalenjin.plan.detailing import promote_due_weeks
from kalenjin.plan.domain import ObjectifRecord, SeanceRecord
from support.fakes import FakeLLMClient

MONDAY = date(2026, 1, 5)


def _objectif(target_date: date) -> ObjectifRecord:
    return ObjectifRecord(
        id=1,
        sport="running",
        target_distance_meters=10_000,
        target_date=target_date,
        target_time_seconds=None,
        created_at=datetime(2026, 1, 1, 8, 0),
    )


def _coarse_seance(id: int, week_start: date, week_volume_meters: float = 20_000) -> SeanceRecord:
    return SeanceRecord(
        id=id,
        plan_id=1,
        week_start=week_start,
        phase="base",
        detail="coarse",
        scheduled_date=None,
        seance_type=None,
        distance_meters=None,
        theme="Base — ~20km target volume",
        week_volume_meters=week_volume_meters,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def _week_response() -> str:
    return json.dumps(
        [
            {"day_offset": 0, "type": "easy", "distance_meters": 7000},
            {"day_offset": 3, "type": "easy", "distance_meters": 7000},
            {"day_offset": 6, "type": "long_run", "distance_meters": 6000},
        ]
    )


def test_promotes_a_coarse_week_once_it_enters_the_detail_horizon() -> None:
    llm = FakeLLMClient(_week_response())
    due = _coarse_seance(1, week_start=MONDAY)
    not_due = _coarse_seance(2, week_start=MONDAY + timedelta(weeks=6))

    result = promote_due_weeks(
        [due, not_due], objectif=_objectif(MONDAY + timedelta(weeks=10)), llm=llm, today=MONDAY
    )

    assert result.removed_seance_ids == [1]
    assert len(result.new_seances) == 3
    assert all(s.detail == "detailed" for s in result.new_seances)


def test_leaves_far_term_coarse_weeks_untouched() -> None:
    llm = FakeLLMClient(_week_response())
    not_due = _coarse_seance(2, week_start=MONDAY + timedelta(weeks=6))

    result = promote_due_weeks(
        [not_due], objectif=_objectif(MONDAY + timedelta(weeks=10)), llm=llm, today=MONDAY
    )

    assert result.removed_seance_ids == []
    assert result.new_seances == []


def test_never_touches_already_detailed_seances() -> None:
    llm = FakeLLMClient(_week_response())
    detailed = SeanceRecord(
        id=3,
        plan_id=1,
        week_start=MONDAY,
        phase="base",
        detail="detailed",
        scheduled_date=MONDAY,
        seance_type="easy",
        distance_meters=5000,
        theme=None,
        week_volume_meters=20_000,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )

    result = promote_due_weeks(
        [detailed], objectif=_objectif(MONDAY + timedelta(weeks=10)), llm=llm, today=MONDAY
    )

    assert result.removed_seance_ids == []
    assert result.new_seances == []
