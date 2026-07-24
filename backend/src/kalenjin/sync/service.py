from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from kalenjin.sync.domain import ActivityRepository, ActivitySource
from kalenjin.sync.parser import parse_activity

HISTORICAL_IMPORT_START = date(2000, 1, 1)
"""Earliest date to fetch on first sync. Garmin has no activities before this,
so it effectively means "all of the user's history"."""

MAX_FETCH_SPAN_DAYS = 365
"""Widest single date range requested from the Garmin API per call. A years-wide
historical import is split into chunks of this size: Garmin's API is not
guaranteed to return a full multi-year window in one response, so a single
giant request risks silently truncating history rather than erroring."""


@dataclass(frozen=True)
class SyncResult:
    imported_count: int


def sync_activities(
    source: ActivitySource,
    repo: ActivityRepository,
    today: date,
    max_fetch_span_days: int = MAX_FETCH_SPAN_DAYS,
) -> SyncResult:
    """Import the user's full history on first run, else sync incrementally.

    Re-fetching a date range whose activities are already persisted is safe:
    `repo.upsert_many` only counts genuinely new activities, so re-running this
    function is idempotent (see ADR-0001, `CONTEXT.md`'s `Séance`).
    """
    if repo.has_any():
        latest_started_at = repo.latest_started_at()
        # has_any() is True, so a record necessarily exists.
        assert latest_started_at is not None
        start_date = latest_started_at.date()
    else:
        start_date = HISTORICAL_IMPORT_START

    raw_activities: list[dict[str, Any]] = []
    for chunk_start, chunk_end in _date_chunks(start_date, today, max_fetch_span_days):
        raw_activities.extend(source.fetch_activities(chunk_start, chunk_end))

    records = [parse_activity(raw) for raw in raw_activities]

    imported_count = repo.upsert_many(records)
    return SyncResult(imported_count=imported_count)


def _date_chunks(start: date, end: date, max_span_days: int) -> Iterator[tuple[date, date]]:
    if start > end:
        return

    span = timedelta(days=max_span_days)
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + span, end)
        yield (chunk_start, chunk_end)
        chunk_start = chunk_end + timedelta(days=1)
