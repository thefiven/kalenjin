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
    """Pushes upcoming, not-yet-completed detailed séances to Garmin Connect (issue #5).

    Kalenjin is always the source of truth (ADR-0001): an already-pushed séance is
    deleted and re-uploaded rather than left stale, since `python-garminconnect` has
    no in-place update — this still satisfies "no duplicate", it just means the
    Garmin-side workout id changes on every push of an already-pushed séance, not only
    when its content changed. Coarse weeks, completed/skipped séances, and past dates
    are never touched.
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
