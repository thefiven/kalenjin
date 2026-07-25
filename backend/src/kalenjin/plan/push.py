from __future__ import annotations

from dataclasses import replace
from datetime import date

from kalenjin.plan.domain import GarminPushClient, PlanRepository, SeanceRecord


def _is_pushable(seance: SeanceRecord, today: date) -> bool:
    return (
        seance.detail == "detailed"
        and seance.status == "pending"
        and seance.scheduled_date is not None
        and seance.scheduled_date >= today
    )


def sync_plan_to_garmin(
    seances: list[SeanceRecord],
    sport: str,
    client: GarminPushClient,
    plan_repo: PlanRepository,
    today: date,
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

    Each successful push is persisted to `plan_repo` and committed immediately, before
    moving to the next séance in the batch — a plain `update_seances` call alone would
    only stage the write in the request's ambient session, which `db.session.session_scope`
    would roll back along with everything else if a later séance in this same batch
    fails. Committing per item makes each success durable independent of what happens
    next: the next sync sees the real `garmin_workout_id` and won't re-push (and
    duplicate) it; only the séance that failed, and any after it, are retried.

    Still not atomic per séance: if `push_workout` fails after `delete_workout`
    succeeded for an already-pushed séance, that séance is left unscheduled on Garmin
    Connect until the next successful push — there's no rollback, since Garmin's API
    gives us nothing to roll back to.
    """
    updated: list[SeanceRecord] = []
    for seance in seances:
        if not _is_pushable(seance, today):
            continue

        if seance.garmin_workout_id is not None:
            client.delete_workout(seance.garmin_workout_id)

        workout_id = client.push_workout(seance, sport)
        pushed = replace(seance, garmin_workout_id=workout_id)
        plan_repo.update_seances([pushed])
        plan_repo.commit()
        updated.append(pushed)

    return updated
