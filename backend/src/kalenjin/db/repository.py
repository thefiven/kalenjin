from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from kalenjin.db.models import Activity
from kalenjin.sync.domain import ActivityRecord, DateRange


def _to_record(activity: Activity) -> ActivityRecord:
    return ActivityRecord(
        garmin_activity_id=activity.garmin_activity_id,
        sport=activity.sport,
        started_at=activity.started_at,
        duration_seconds=activity.duration_seconds,
        distance_meters=activity.distance_meters,
        average_heart_rate=activity.average_heart_rate,
        raw_payload=activity.raw_payload,
    )


class SqlAlchemyActivityRepository:
    """`sync.domain.ActivityRepository` backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def has_any(self) -> bool:
        return self._session.execute(select(Activity.id).limit(1)).first() is not None

    def latest_started_at(self) -> datetime | None:
        return self._session.execute(select(func.max(Activity.started_at))).scalar_one_or_none()

    def upsert_many(self, activities: list[ActivityRecord]) -> int:
        if not activities:
            return 0

        inserted = 0
        for activity in activities:
            stmt = (
                insert(Activity)
                .values(
                    garmin_activity_id=activity.garmin_activity_id,
                    sport=activity.sport,
                    started_at=activity.started_at,
                    duration_seconds=activity.duration_seconds,
                    distance_meters=activity.distance_meters,
                    average_heart_rate=activity.average_heart_rate,
                    raw_payload=activity.raw_payload,
                    created_at=datetime.now(),
                )
                .on_conflict_do_nothing(constraint="uq_activities_garmin_activity_id")
                .returning(Activity.id)
            )
            if self._session.execute(stmt).first() is not None:
                inserted += 1

        return inserted

    def list_activities(self, date_range: DateRange = DateRange()) -> list[ActivityRecord]:
        stmt = select(Activity).order_by(Activity.started_at.desc())
        if date_range.since is not None:
            stmt = stmt.where(Activity.started_at >= datetime.combine(date_range.since, time.min))
        if date_range.until is not None:
            stmt = stmt.where(Activity.started_at <= datetime.combine(date_range.until, time.max))

        activities = self._session.execute(stmt).scalars().all()
        return [_to_record(activity) for activity in activities]

    def get_activity(self, garmin_activity_id: str) -> ActivityRecord | None:
        stmt = select(Activity).where(Activity.garmin_activity_id == garmin_activity_id)
        activity = self._session.execute(stmt).scalar_one_or_none()
        return None if activity is None else _to_record(activity)
