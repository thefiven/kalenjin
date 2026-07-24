from datetime import date

import pytest
from garminconnect.workout import ConditionType, CyclingWorkout, RunningWorkout

from kalenjin.garmin.workout_builder import build_workout
from kalenjin.plan.domain import SeanceRecord


def _seance(seance_type: str = "easy", distance_meters: float | None = 5000.0) -> SeanceRecord:
    return SeanceRecord(
        id=1,
        plan_id=1,
        week_start=date(2026, 1, 5),
        phase="base",
        detail="detailed",
        scheduled_date=date(2026, 1, 5),
        seance_type=seance_type,  # type: ignore[arg-type]
        distance_meters=distance_meters,
        theme=None,
        week_volume_meters=20_000,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def test_builds_a_running_workout_for_running() -> None:
    workout = build_workout(_seance(), sport="running")

    assert isinstance(workout, RunningWorkout)


def test_builds_a_cycling_workout_for_cycling() -> None:
    workout = build_workout(_seance(), sport="cycling")

    assert isinstance(workout, CyclingWorkout)


def test_raises_for_an_unsupported_sport() -> None:
    with pytest.raises(ValueError, match="swimming"):
        build_workout(_seance(), sport="swimming")


def test_raises_when_the_seance_has_no_distance() -> None:
    with pytest.raises(ValueError, match="distance"):
        build_workout(_seance(distance_meters=None), sport="running")


def test_the_single_step_ends_on_the_seance_distance() -> None:
    workout = build_workout(_seance(distance_meters=8000.0), sport="running")

    step = workout.workoutSegments[0].workoutSteps[0]

    assert step.endCondition is not None
    assert step.endCondition["conditionTypeId"] == ConditionType.DISTANCE
    assert step.endConditionValue == 8000.0


def test_the_workout_name_reflects_the_seance_type() -> None:
    workout = build_workout(_seance(seance_type="tempo"), sport="running")

    assert "tempo" in workout.workoutName.lower()


def test_estimated_duration_is_positive_and_scales_with_distance() -> None:
    short = build_workout(_seance(distance_meters=3000.0), sport="running")
    long = build_workout(_seance(distance_meters=15000.0), sport="running")

    assert short.estimatedDurationInSecs > 0
    assert long.estimatedDurationInSecs > short.estimatedDurationInSecs
