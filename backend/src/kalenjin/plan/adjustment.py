from __future__ import annotations

from dataclasses import replace
from datetime import date

from kalenjin.plan.domain import SeanceRecord, is_upcoming_seance
from kalenjin.rapport.domain import RapportRecord

BACKOFF_FACTOR = 0.85
HARD_STOP_RECOVERY_SHARE = 0.15
CONSECUTIVE_HIGH_EFFORT_THRESHOLD = 2
_HARD_STOP_FLAGS = frozenset({"pain", "illness"})


def _consecutive_high_effort_count(rapports: list[RapportRecord]) -> int:
    count = 0
    for rapport in rapports:
        if rapport.perceived_effort != "high" or rapport.flag in _HARD_STOP_FLAGS:
            break
        count += 1
    return count


def _hard_stop(adjustable: list[SeanceRecord]) -> list[SeanceRecord]:
    soonest = min(adjustable, key=lambda s: s.scheduled_date or date.max)
    recovery_distance = min(
        soonest.distance_meters or 0, soonest.week_volume_meters * HARD_STOP_RECOVERY_SHARE
    )
    return [replace(soonest, seance_type="easy", distance_meters=recovery_distance)]


def _back_off(adjustable: list[SeanceRecord]) -> list[SeanceRecord]:
    return [
        replace(s, distance_meters=(s.distance_meters or 0) * BACKOFF_FACTOR) for s in adjustable
    ]


def adjust_plan_for_rapport(
    seances: list[SeanceRecord],
    rapport: RapportRecord,
    recent_rapports: list[RapportRecord],
    today: date,
) -> list[SeanceRecord]:
    """The Rapport-driven adjustment guardrails from the approved ruleset (issue #4).

    Only ever mutates séances that are detailed, pending, and not yet in the past —
    completed séances, the past, and still-coarse weeks are untouched. Returns the
    (possibly empty) list of updated séances for the caller to persist; never mutates
    `seances` in place.

    - `flag` of "pain"/"illness" is a hard stop: the single soonest upcoming séance
      becomes an easy recovery session, regardless of what the plan said.
    - Two or more consecutive "high" perceived-effort reports (this rapport plus
      `recent_rapports`, most-recent-first) trigger a flat, capped backoff on every
      upcoming pending séance — never an increase.
    - Otherwise, no adjustment: the pre-committed plan stands.
    """
    adjustable = [s for s in seances if is_upcoming_seance(s, today)]
    if not adjustable:
        return []

    if rapport.flag in _HARD_STOP_FLAGS:
        return _hard_stop(adjustable)

    if (
        _consecutive_high_effort_count([rapport, *recent_rapports])
        >= CONSECUTIVE_HIGH_EFFORT_THRESHOLD
    ):
        return _back_off(adjustable)

    return []
