from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from kalenjin.sync.domain import ActivityRepository, ActivitySource
from kalenjin.sync.parser import parse_activity

HISTORICAL_IMPORT_START = date(2000, 1, 1)
"""Earliest date to fetch on first sync. Garmin has no activities before this,
so it effectively means "all of the user's history"."""


@dataclass(frozen=True)
class SyncResult:
    imported_count: int


def sync_activities(source: ActivitySource, repo: ActivityRepository, today: date) -> SyncResult:
    """Import the user's full history on first run, else sync incrementally.

    Re-fetching a date range whose activities are already persisted is safe:
    `repo.upsert_many` only counts genuinely new activities, so re-running this
    function is idempotent (see ADR-0001, `CONTEXT.md`'s `Séance`).
    """
    latest_started_at = repo.latest_started_at()
    start_date = (
        latest_started_at.date() if latest_started_at is not None else HISTORICAL_IMPORT_START
    )

    raw_activities = source.fetch_activities(start_date, today)
    records = [parse_activity(raw) for raw in raw_activities]

    imported_count = repo.upsert_many(records)
    return SyncResult(imported_count=imported_count)
