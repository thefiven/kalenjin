from datetime import date, datetime

from kalenjin.sync.domain import ActivityRecord
from kalenjin.sync.service import HISTORICAL_IMPORT_START, sync_activities
from support.fakes import FakeRepository, FakeSource, raw_activity


def test_empty_repository_triggers_full_historical_import() -> None:
    today = date(2024, 6, 10)
    # A max_fetch_span_days wider than the whole range keeps this a single call —
    # chunking itself is covered by its own tests below.
    source = FakeSource({(HISTORICAL_IMPORT_START, today): [raw_activity("1")]})
    repo = FakeRepository()

    result = sync_activities(source, repo, today=today, max_fetch_span_days=100_000)

    assert source.calls == [(HISTORICAL_IMPORT_START, today)]
    assert result.imported_count == 1


def test_non_empty_repository_syncs_incrementally_from_latest_activity() -> None:
    today = date(2024, 6, 10)
    last_synced = datetime(2024, 6, 5, 8, 0, 0)
    existing = ActivityRecord(
        garmin_activity_id="1",
        sport="running",
        started_at=last_synced,
        duration_seconds=1800,
        distance_meters=5000,
        average_heart_rate=150,
        raw_payload={},
    )
    source = FakeSource({(last_synced.date(), today): [raw_activity("2", "2024-06-06 07:00:00")]})
    repo = FakeRepository(existing=[existing])

    result = sync_activities(source, repo, today=today)

    assert source.calls == [(last_synced.date(), today)]
    assert result.imported_count == 1


def test_reimporting_the_same_activity_is_not_counted_as_new() -> None:
    today = date(2024, 6, 10)
    source = FakeSource({(HISTORICAL_IMPORT_START, today): [raw_activity("1")]})
    repo = FakeRepository()

    sync_activities(source, repo, today=today, max_fetch_span_days=100_000)
    second_result = sync_activities(source, repo, today=today, max_fetch_span_days=100_000)

    assert second_result.imported_count == 0


def test_no_activities_returned_yields_zero_imported() -> None:
    today = date(2024, 6, 10)
    source = FakeSource({})
    repo = FakeRepository()

    result = sync_activities(source, repo, today=today)

    assert result.imported_count == 0


def test_wide_date_range_is_fetched_in_bounded_chunks() -> None:
    """A multi-year historical import must not be requested as one giant range —
    Garmin's API isn't guaranteed to return a full multi-year window in one call."""
    today = date(2000, 1, 22)
    source = FakeSource({})
    repo = FakeRepository()

    sync_activities(source, repo, today=today, max_fetch_span_days=10)

    assert source.calls == [
        (date(2000, 1, 1), date(2000, 1, 11)),
        (date(2000, 1, 12), date(2000, 1, 22)),
    ]
    assert all((end - start).days <= 10 for start, end in source.calls)


def test_chunked_results_are_all_aggregated_and_persisted() -> None:
    today = date(2000, 1, 15)
    source = FakeSource(
        {
            (date(2000, 1, 1), date(2000, 1, 6)): [raw_activity("1", "2000-01-02 07:00:00")],
            (date(2000, 1, 7), date(2000, 1, 12)): [raw_activity("2", "2000-01-08 07:00:00")],
            (date(2000, 1, 13), date(2000, 1, 15)): [raw_activity("3", "2000-01-14 07:00:00")],
        }
    )
    repo = FakeRepository()

    result = sync_activities(source, repo, today=today, max_fetch_span_days=5)

    assert result.imported_count == 3
