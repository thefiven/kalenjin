from __future__ import annotations

from garminconnect.workout import (
    ConditionType,
    CyclingWorkout,
    ExecutableStep,
    RunningWorkout,
    SportType,
    StepType,
    TargetType,
    WorkoutSegment,
)

from kalenjin.plan.domain import SeanceRecord

# `garminconnect` 0.3.6 (the pinned floor in pyproject.toml) doesn't yet ship a
# distance-based step helper (only time-based create_*_step functions) — the step
# below is built directly from ExecutableStep instead.

_SPORTS: dict[str, tuple[type[RunningWorkout | CyclingWorkout], int]] = {
    "running": (RunningWorkout, SportType.RUNNING),
    "cycling": (CyclingWorkout, SportType.CYCLING),
}

# A rough pace estimate purely for the workout's display duration — Garmin requires
# `estimatedDurationInSecs`, but the step's actual end condition is distance-based
# (see `_distance_step`), so an imprecise estimate doesn't affect what the watch runs.
_ROUGH_PACE_SECONDS_PER_KM: dict[str, float] = {"running": 360.0, "cycling": 150.0}


def _distance_step(distance_meters: float) -> ExecutableStep:
    return ExecutableStep(
        stepOrder=1,
        stepType={"stepTypeId": StepType.MAIN, "stepTypeKey": "main", "displayOrder": 8},
        endCondition={
            "conditionTypeId": ConditionType.DISTANCE,
            "conditionTypeKey": "distance",
            "displayOrder": 3,
            "displayable": True,
        },
        endConditionValue=distance_meters,
        targetType={
            "workoutTargetTypeId": TargetType.NO_TARGET,
            "workoutTargetTypeKey": "no.target",
            "displayOrder": 1,
        },
    )


def build_workout(seance: SeanceRecord, sport: str) -> RunningWorkout | CyclingWorkout:
    """Maps a detailed `SeanceRecord` to a typed Garmin Connect workout (issue #5).

    A single main step ending on distance — `SeanceRecord` only carries a séance type
    label and a total distance, not a segmented interval/tempo structure, so a
    multi-segment workout would be inventing data the plan doesn't have.
    """
    if sport not in _SPORTS:
        raise ValueError(f"Garmin workout push isn't supported for sport {sport!r}")
    if seance.distance_meters is None:
        raise ValueError("Cannot build a Garmin workout for a séance with no distance_meters")

    workout_class, sport_type_id = _SPORTS[sport]
    segment = WorkoutSegment(
        segmentOrder=1,
        sportType={"sportTypeId": sport_type_id, "sportTypeKey": sport, "displayOrder": 1},
        workoutSteps=[_distance_step(seance.distance_meters)],
    )
    estimated_duration = round(seance.distance_meters / 1000 * _ROUGH_PACE_SECONDS_PER_KM[sport])

    return workout_class(
        workoutName=f"Kalenjin — {seance.seance_type} ({seance.distance_meters / 1000:.1f}km)",
        estimatedDurationInSecs=estimated_duration,
        workoutSegments=[segment],
    )
