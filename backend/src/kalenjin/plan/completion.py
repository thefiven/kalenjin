from __future__ import annotations

from dataclasses import replace
from datetime import date

from kalenjin.plan.domain import SeanceRecord
from kalenjin.sync.domain import ActivityRecord


def match_completed_seances(
    seances: list[SeanceRecord], activities: list[ActivityRecord], today: date
) -> list[SeanceRecord]:
    """Marks past-due detailed séances completed/skipped against realized activities.

    A séance is matched to the first activity whose start date equals its
    `scheduled_date` — a best-effort link (issue #4 doesn't specify a stronger
    matching rule) that feeds the dashboard's plan-adherence metric and gives
    `garmin_activity_id` a value once a session is realized.
    """
    activities_by_date = {activity.started_at.date(): activity for activity in activities}

    updated: list[SeanceRecord] = []
    for seance in seances:
        if (
            seance.detail != "detailed"
            or seance.status != "pending"
            or seance.scheduled_date is None
            or seance.scheduled_date >= today
        ):
            continue

        match = activities_by_date.get(seance.scheduled_date)
        if match is not None:
            updated.append(
                replace(seance, status="completed", garmin_activity_id=match.garmin_activity_id)
            )
        else:
            updated.append(replace(seance, status="skipped"))

    return updated
