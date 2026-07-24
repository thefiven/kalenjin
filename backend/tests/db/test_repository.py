from datetime import date, datetime

import pytest
from sqlalchemy.orm import Session

from kalenjin.db.repository import SqlAlchemyActivityRepository
from kalenjin.sync.domain import ActivityRecord, DateRange

pytestmark = pytest.mark.integration


def _record(activity_id: str, started_at: datetime = datetime(2024, 6, 1, 7, 30)) -> ActivityRecord:
    return ActivityRecord(
        garmin_activity_id=activity_id,
        sport="running",
        started_at=started_at,
        duration_seconds=1800.0,
        distance_meters=5000.0,
        average_heart_rate=150.0,
        raw_payload={"activityId": activity_id},
    )


def test_has_any_is_false_when_empty(db_session: Session) -> None:
    repo = SqlAlchemyActivityRepository(db_session)

    assert repo.has_any() is False


def test_upsert_many_inserts_new_activities(db_session: Session) -> None:
    repo = SqlAlchemyActivityRepository(db_session)

    inserted = repo.upsert_many([_record("1"), _record("2")])

    assert inserted == 2
    assert repo.has_any() is True


def test_upsert_many_does_not_duplicate_on_re_import(db_session: Session) -> None:
    repo = SqlAlchemyActivityRepository(db_session)
    repo.upsert_many([_record("1")])

    inserted_again = repo.upsert_many([_record("1")])

    assert inserted_again == 0


def test_latest_started_at_returns_the_max_start_time(db_session: Session) -> None:
    repo = SqlAlchemyActivityRepository(db_session)
    repo.upsert_many(
        [
            _record("1", datetime(2024, 6, 1, 7, 30)),
            _record("2", datetime(2024, 6, 5, 8, 0)),
        ]
    )

    assert repo.latest_started_at() == datetime(2024, 6, 5, 8, 0)


def test_list_activities_returns_them_most_recent_first(db_session: Session) -> None:
    repo = SqlAlchemyActivityRepository(db_session)
    repo.upsert_many(
        [
            _record("1", datetime(2024, 6, 1, 7, 30)),
            _record("2", datetime(2024, 6, 5, 8, 0)),
        ]
    )

    activities = repo.list_activities()

    assert [a.garmin_activity_id for a in activities] == ["2", "1"]


def test_list_activities_filters_by_since_and_until(db_session: Session) -> None:
    repo = SqlAlchemyActivityRepository(db_session)
    repo.upsert_many(
        [
            _record("1", datetime(2024, 5, 1, 7, 30)),
            _record("2", datetime(2024, 6, 5, 8, 0)),
            _record("3", datetime(2024, 7, 1, 8, 0)),
        ]
    )

    activities = repo.list_activities(DateRange(since=date(2024, 6, 1), until=date(2024, 6, 30)))

    assert [a.garmin_activity_id for a in activities] == ["2"]


def test_get_activity_returns_the_matching_record(db_session: Session) -> None:
    repo = SqlAlchemyActivityRepository(db_session)
    repo.upsert_many([_record("1"), _record("2")])

    activity = repo.get_activity("2")

    assert activity is not None
    assert activity.garmin_activity_id == "2"


def test_get_activity_returns_none_when_missing(db_session: Session) -> None:
    repo = SqlAlchemyActivityRepository(db_session)

    assert repo.get_activity("does-not-exist") is None
