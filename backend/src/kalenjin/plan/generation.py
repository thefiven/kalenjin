from __future__ import annotations

import json
from datetime import date, timedelta
from itertools import pairwise
from typing import Any

from kalenjin.llm.domain import LLMClient
from kalenjin.plan.domain import HARD_SEANCE_TYPES, ObjectifRecord, SeanceRecord
from kalenjin.plan.periodization import Phase, WeekTarget, compute_week_targets
from kalenjin.sync.domain import ActivityRecord

DETAIL_HORIZON_DAYS = 14
MIN_HARD_SEANCE_GAP_DAYS = 2
VOLUME_TOLERANCE = 0.15
DEFAULT_STARTING_WEEKLY_VOLUME_METERS = 15_000.0

_ALL_SEANCE_TYPES = frozenset({"easy", "long_run", "tempo", "interval", "rest"})


class PlanGenerationError(Exception):
    """Raised when the LLM's response can't be parsed into valid weekly séances."""


def estimate_current_weekly_volume(
    activities: list[ActivityRecord], today: date, weeks: int = 4
) -> float:
    """Average weekly distance over the last `weeks` completed weeks.

    Falls back to a conservative default for a first-time user with no history —
    `compute_week_targets` requires a positive baseline (see periodization.py).
    """
    window_start = today - timedelta(weeks=weeks)
    total = sum(
        activity.distance_meters or 0
        for activity in activities
        if window_start <= activity.started_at.date() < today
    )
    if total <= 0:
        return DEFAULT_STARTING_WEEKLY_VOLUME_METERS
    return total / weeks


def _strip_code_fences(response: str) -> str:
    text = response.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        text = text.removesuffix("```").strip()
    return text


def _parse_and_validate_seances(response: str, week: WeekTarget) -> list[dict[str, Any]]:
    try:
        payload = json.loads(_strip_code_fences(response))
    except json.JSONDecodeError as exc:
        raise PlanGenerationError(f"LLM response was not valid JSON: {response!r}") from exc

    if not isinstance(payload, list):
        raise PlanGenerationError(f"LLM response was not a JSON array: {response!r}")

    seen_day_offsets: set[int] = set()
    hard_day_offsets: list[int] = []
    total_distance = 0.0
    seances: list[dict[str, Any]] = []

    for entry in payload:
        if not isinstance(entry, dict):
            raise PlanGenerationError(f"seance entry was not an object: {entry!r}")

        day_offset = entry.get("day_offset")
        seance_type = entry.get("type")
        distance_meters = entry.get("distance_meters")

        if (
            not isinstance(day_offset, int)
            or isinstance(day_offset, bool)
            or not (0 <= day_offset <= 6)
        ):
            raise PlanGenerationError(f"invalid day_offset: {entry!r}")
        if day_offset in seen_day_offsets:
            raise PlanGenerationError(f"duplicate day_offset: {entry!r}")
        if seance_type not in _ALL_SEANCE_TYPES:
            raise PlanGenerationError(f"unknown seance type: {entry!r}")
        if (
            not isinstance(distance_meters, int | float)
            or isinstance(distance_meters, bool)
            or distance_meters < 0
        ):
            raise PlanGenerationError(f"invalid distance_meters: {entry!r}")
        if seance_type == "long_run" and distance_meters > week.long_run_cap_meters + 1e-6:
            raise PlanGenerationError(f"long run exceeds the cap: {entry!r}")

        seen_day_offsets.add(day_offset)
        if seance_type in HARD_SEANCE_TYPES:
            hard_day_offsets.append(day_offset)
        total_distance += distance_meters
        seances.append(
            {
                "day_offset": day_offset,
                "type": seance_type,
                "distance_meters": float(distance_meters),
            }
        )

    hard_day_offsets.sort()
    for earlier, later in pairwise(hard_day_offsets):
        if later - earlier < MIN_HARD_SEANCE_GAP_DAYS:
            raise PlanGenerationError(
                f"hard seances scheduled too close together: {hard_day_offsets!r}"
            )

    lower = week.target_volume_meters * (1 - VOLUME_TOLERANCE)
    upper = week.target_volume_meters * (1 + VOLUME_TOLERANCE)
    if not (lower <= total_distance <= upper):
        raise PlanGenerationError(
            f"week total distance {total_distance} is outside tolerance of {week.target_volume_meters}"
        )

    return seances


def _fallback_seances(week: WeekTarget) -> list[dict[str, Any]]:
    """A deterministic template that satisfies the same hard constraints by construction."""
    long_run = min(week.target_volume_meters * 0.3, week.long_run_cap_meters)
    remaining = week.target_volume_meters - long_run

    if week.phase in (Phase.BUILD, Phase.PEAK):
        hard_distance = remaining * 0.25
        easy_total = remaining - hard_distance
        easy_each = easy_total / 3
        return [
            {"day_offset": 0, "type": "easy", "distance_meters": easy_each},
            {"day_offset": 2, "type": "tempo", "distance_meters": hard_distance},
            {"day_offset": 4, "type": "easy", "distance_meters": easy_each},
            {"day_offset": 5, "type": "easy", "distance_meters": easy_each},
            {"day_offset": 6, "type": "long_run", "distance_meters": long_run},
        ]

    easy_each = remaining / 3
    return [
        {"day_offset": 0, "type": "easy", "distance_meters": easy_each},
        {"day_offset": 2, "type": "easy", "distance_meters": easy_each},
        {"day_offset": 4, "type": "easy", "distance_meters": easy_each},
        {"day_offset": 6, "type": "long_run", "distance_meters": long_run},
    ]


def _build_week_prompt(week: WeekTarget, objectif: ObjectifRecord) -> str:
    return (
        "You are a running coach composing one week of a training plan. "
        f"Sport: {objectif.sport}. Week phase: {week.phase.value}. "
        f"Target total distance for the week: {round(week.target_volume_meters)}m. "
        f"Long run must not exceed {round(week.long_run_cap_meters)}m. "
        "Respond with a single JSON array of seance objects, each with exactly three keys: "
        '"day_offset" (integer 0-6, Monday=0, no duplicates), '
        '"type" (one of "easy", "long_run", "tempo", "interval", "rest"), '
        '"distance_meters" (number, 0 for rest days). '
        "Include at most one tempo/interval seance, and if you include one, do not "
        "place it within 2 days of another hard seance. "
        "The sum of all non-rest distance_meters should be close to the week's target total. "
        "Do not include anything other than the JSON array."
    )


def _week_seances(
    week: WeekTarget, objectif: ObjectifRecord, seances: list[dict[str, Any]]
) -> list[SeanceRecord]:
    return [
        SeanceRecord(
            id=None,
            plan_id=None,
            week_start=week.week_start,
            phase=week.phase.value,
            detail="detailed",
            scheduled_date=week.week_start + timedelta(days=int(seance["day_offset"])),
            seance_type=seance["type"],
            distance_meters=seance["distance_meters"],
            theme=None,
            week_volume_meters=week.target_volume_meters,
            status="pending",
            garmin_activity_id=None,
            garmin_workout_id=None,
        )
        for seance in seances
        if seance["type"] != "rest"
    ]


def detail_week(week: WeekTarget, objectif: ObjectifRecord, llm: LLMClient) -> list[SeanceRecord]:
    """Turns one week's target (coarse or not-yet-detailed) into concrete séances.

    Shared by initial plan generation and by `plan/detailing.py`'s promotion of a coarse
    week once it enters the detail horizon.
    """
    response = llm.generate(_build_week_prompt(week, objectif))
    try:
        seances = _parse_and_validate_seances(response, week)
    except PlanGenerationError:
        seances = _fallback_seances(week)
    return _week_seances(week, objectif, seances)


def _coarse_seance(week: WeekTarget) -> SeanceRecord:
    return SeanceRecord(
        id=None,
        plan_id=None,
        week_start=week.week_start,
        phase=week.phase.value,
        detail="coarse",
        scheduled_date=None,
        seance_type=None,
        distance_meters=None,
        theme=week.theme,
        week_volume_meters=week.target_volume_meters,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def generate_plan_seances(
    objectif: ObjectifRecord,
    llm: LLMClient,
    today: date,
    current_weekly_volume_meters: float,
) -> list[SeanceRecord]:
    """Builds the full séance sequence for a new plan (ADR-0001, issue #4).

    Near-term weeks (within `DETAIL_HORIZON_DAYS`) are detailed via the LLM, validated
    against the approved hard constraints, with a deterministic fallback on violation.
    Far-term weeks stay coarse — see `plan/detailing.py` for promoting them later.
    """
    week_targets = compute_week_targets(
        target_distance_meters=objectif.target_distance_meters,
        target_date=objectif.target_date,
        today=today,
        current_weekly_volume_meters=current_weekly_volume_meters,
    )

    seances: list[SeanceRecord] = []
    for week in week_targets:
        if week.week_start < today + timedelta(days=DETAIL_HORIZON_DAYS):
            seances.extend(detail_week(week, objectif, llm))
        else:
            seances.append(_coarse_seance(week))
    return seances
