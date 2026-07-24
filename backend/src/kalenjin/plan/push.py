from __future__ import annotations

from dataclasses import replace
from datetime import date

from kalenjin.plan.domain import GarminPushClient, SeanceRecord


def _is_pushable(seance: SeanceRecord, today: date) -> bool:
    return (
        seance.detail == "detailed"
        and seance.status == "pending"
        and seance.scheduled_date is not None
        and seance.scheduled_date >= today
    )


def sync_plan_to_garmin(
    seances: list[SeanceRecord], sport: str, client: GarminPushClient, today: date
) -> list[SeanceRecord]:
    """Pushes the given séances to Garmin Connect (issue #5), skipping any that are
    coarse, completed/skipped, or scheduled in the past.

    Kalenjin is always the source of truth (ADR-0001): a séance that already has a
    `garmin_workout_id` is deleted and re-uploaded rather than left stale, since
    `python-garminconnect` has no in-place update — this still satisfies "no
    duplicate", it just means the Garmin-side workout id changes every time this
    function is called for an already-pushed séance. Callers are responsible for only
    passing séances that actually need (re-)pushing — see `api.py`'s `/sync` (only
    never-pushed séances, to avoid churning unchanged ones on every sync) and its
    rapport endpoint (only the séances `adjust_plan_for_rapport` actually changed).

    Not atomic: if `push_workout` fails after `delete_workout` succeeded for an
    already-pushed séance, that séance is left unscheduled on Garmin Connect until the
    next successful push — there's no rollback, since Garmin's API gives us nothing to
    roll back to.
    """
    updated: list[SeanceRecord] = []
    for seance in seances:
        if not _is_pushable(seance, today):
            continue

        if seance.garmin_workout_id is not None:
            client.delete_workout(seance.garmin_workout_id)

        workout_id = client.push_workout(seance, sport)
        updated.append(replace(seance, garmin_workout_id=workout_id))

    return updated
