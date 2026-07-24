from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

WEEKLY_VOLUME_GROWTH_CAP = 1.10
CUTBACK_INTERVAL_WEEKS = 4
CUTBACK_VOLUME_FACTOR = 0.725

MARATHON_THRESHOLD_METERS = 30_000
HALF_MARATHON_THRESHOLD_METERS = 15_000
MARATHON_LONG_RUN_CEILING_METERS = 32_000
HALF_MARATHON_LONG_RUN_CEILING_METERS = 24_000
LONG_RUN_SHARE_OF_WEEKLY_VOLUME = 0.30

# Taper multipliers are relative to the peak (last non-taper) week's volume, applied
# in order — not chained week-over-week, since a taper is a deliberate drop from peak,
# not a further 10%-rule reduction of the previous taper week.
TAPER_MULTIPLIERS: dict[int, tuple[float, ...]] = {
    1: (0.6,),
    2: (0.7, 0.5),
    3: (0.75, 0.6, 0.4),
}


class Phase(str, Enum):
    BASE = "base"
    BUILD = "build"
    PEAK = "peak"
    TAPER = "taper"


@dataclass(frozen=True)
class WeekTarget:
    week_start: date
    phase: Phase
    target_volume_meters: float
    is_cutback: bool
    long_run_cap_meters: float
    theme: str


def _monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _taper_weeks_for(target_distance_meters: float) -> int:
    if target_distance_meters >= MARATHON_THRESHOLD_METERS:
        return 3
    if target_distance_meters >= HALF_MARATHON_THRESHOLD_METERS:
        return 2
    return 1


def _long_run_ceiling_for(target_distance_meters: float) -> float:
    if target_distance_meters >= MARATHON_THRESHOLD_METERS:
        return MARATHON_LONG_RUN_CEILING_METERS
    if target_distance_meters >= HALF_MARATHON_THRESHOLD_METERS:
        return HALF_MARATHON_LONG_RUN_CEILING_METERS
    return target_distance_meters * 1.5


def long_run_cap_for(target_volume_meters: float, target_distance_meters: float) -> float:
    return min(
        target_volume_meters * LONG_RUN_SHARE_OF_WEEKLY_VOLUME,
        _long_run_ceiling_for(target_distance_meters),
    )


def _theme_for(phase: Phase, target_volume_meters: float, is_cutback: bool) -> str:
    label = "Cutback" if is_cutback else phase.value.capitalize()
    return f"{label} — ~{round(target_volume_meters / 1000)}km target volume"


def compute_week_targets(
    *,
    target_distance_meters: float,
    target_date: date,
    today: date,
    current_weekly_volume_meters: float,
) -> list[WeekTarget]:
    """The deterministic, safety-critical periodization core (see ADR-0001 and issue #4).

    Computes one target per Monday-aligned week from `today` through the goal week,
    applying the approved ruleset: the 10%-rule volume cap, a cutback week every 4th
    non-taper week, and a taper sized to the goal distance. This is intentionally free
    of any LLM call — the numeric guardrails are code, not model output (see
    `plan/generation.py`, which composes concrete sessions on top of these targets).
    """
    if target_date < today:
        raise ValueError("target_date must not be in the past")
    if current_weekly_volume_meters <= 0:
        raise ValueError("current_weekly_volume_meters must be positive")

    first_week_start = _monday_of(today)
    goal_week_start = _monday_of(target_date)
    total_weeks = (goal_week_start - first_week_start).days // 7 + 1

    taper_weeks = min(_taper_weeks_for(target_distance_meters), total_weeks)
    non_taper_weeks = total_weeks - taper_weeks

    base_weeks = non_taper_weeks // 2
    peak_weeks = 1 if non_taper_weeks >= 4 else 0
    build_weeks = non_taper_weeks - base_weeks - peak_weeks

    phases = (
        [Phase.BASE] * base_weeks
        + [Phase.BUILD] * build_weeks
        + [Phase.PEAK] * peak_weeks
        + [Phase.TAPER] * taper_weeks
    )

    weeks: list[WeekTarget] = []
    peak_volume = current_weekly_volume_meters
    for index, phase in enumerate(phases):
        week_start = first_week_start + timedelta(weeks=index)

        if phase == Phase.TAPER:
            taper_index = index - non_taper_weeks
            multiplier = TAPER_MULTIPLIERS[taper_weeks][taper_index]
            volume = peak_volume * multiplier
            is_cutback = False
        elif index == 0:
            volume = current_weekly_volume_meters
            is_cutback = False
        else:
            previous = weeks[index - 1]
            is_cutback = (index + 1) % CUTBACK_INTERVAL_WEEKS == 0
            volume = (
                previous.target_volume_meters * CUTBACK_VOLUME_FACTOR
                if is_cutback
                else previous.target_volume_meters * WEEKLY_VOLUME_GROWTH_CAP
            )
            peak_volume = max(peak_volume, volume)

        weeks.append(
            WeekTarget(
                week_start=week_start,
                phase=phase,
                target_volume_meters=volume,
                is_cutback=is_cutback,
                long_run_cap_meters=long_run_cap_for(volume, target_distance_meters),
                theme=_theme_for(phase, volume, is_cutback),
            )
        )

    return weeks
