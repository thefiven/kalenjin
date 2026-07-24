from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from kalenjin.db.models import Activity, Objectif, Plan, Rapport, Seance
from kalenjin.plan.domain import ObjectifRecord, PlanRecord, SeanceRecord
from kalenjin.rapport.domain import RapportRecord
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


def _to_rapport(rapport: Rapport) -> RapportRecord:
    return RapportRecord(
        garmin_activity_id=rapport.garmin_activity_id,
        strengths=rapport.strengths,
        improvements=rapport.improvements,
        generated_at=rapport.generated_at,
        completed_as_planned=rapport.completed_as_planned,
        perceived_effort=rapport.perceived_effort,  # type: ignore[arg-type]
        flag=rapport.flag,  # type: ignore[arg-type]
    )


class SqlAlchemyRapportRepository:
    """`rapport.domain.RapportRepository` backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, rapport: RapportRecord) -> None:
        stmt = (
            insert(Rapport)
            .values(
                garmin_activity_id=rapport.garmin_activity_id,
                strengths=rapport.strengths,
                improvements=rapport.improvements,
                generated_at=rapport.generated_at,
                completed_as_planned=rapport.completed_as_planned,
                perceived_effort=rapport.perceived_effort,
                flag=rapport.flag,
            )
            .on_conflict_do_update(
                constraint="uq_rapports_garmin_activity_id",
                set_={
                    "strengths": rapport.strengths,
                    "improvements": rapport.improvements,
                    "generated_at": rapport.generated_at,
                    "completed_as_planned": rapport.completed_as_planned,
                    "perceived_effort": rapport.perceived_effort,
                    "flag": rapport.flag,
                },
            )
        )
        self._session.execute(stmt)

    def get_for_activity(self, garmin_activity_id: str) -> RapportRecord | None:
        stmt = select(Rapport).where(Rapport.garmin_activity_id == garmin_activity_id)
        rapport = self._session.execute(stmt).scalar_one_or_none()
        return None if rapport is None else _to_rapport(rapport)

    def list_recent(self, limit: int) -> list[RapportRecord]:
        stmt = select(Rapport).order_by(Rapport.generated_at.desc()).limit(limit)
        rapports = self._session.execute(stmt).scalars().all()
        return [_to_rapport(r) for r in rapports]


def _to_objectif(objectif: Objectif) -> ObjectifRecord:
    return ObjectifRecord(
        id=objectif.id,
        sport=objectif.sport,
        target_distance_meters=objectif.target_distance_meters,
        target_date=objectif.target_date,
        target_time_seconds=objectif.target_time_seconds,
        created_at=objectif.created_at,
    )


class SqlAlchemyObjectifRepository:
    """`plan.domain.ObjectifRepository` backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, objectif: ObjectifRecord) -> ObjectifRecord:
        row = Objectif(
            sport=objectif.sport,
            target_distance_meters=objectif.target_distance_meters,
            target_date=objectif.target_date,
            target_time_seconds=objectif.target_time_seconds,
            created_at=objectif.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return _to_objectif(row)

    def get_active(self) -> ObjectifRecord | None:
        stmt = select(Objectif).order_by(Objectif.created_at.desc(), Objectif.id.desc()).limit(1)
        row = self._session.execute(stmt).scalar_one_or_none()
        return None if row is None else _to_objectif(row)


def _to_seance(seance: Seance) -> SeanceRecord:
    return SeanceRecord(
        id=seance.id,
        plan_id=seance.plan_id,
        week_start=seance.week_start,
        phase=seance.phase,
        detail=seance.detail,  # type: ignore[arg-type]
        scheduled_date=seance.scheduled_date,
        seance_type=seance.seance_type,  # type: ignore[arg-type]
        distance_meters=seance.distance_meters,
        theme=seance.theme,
        week_volume_meters=seance.week_volume_meters,
        status=seance.status,  # type: ignore[arg-type]
        garmin_activity_id=seance.garmin_activity_id,
    )


def _seance_row(seance: SeanceRecord, plan_id: int) -> Seance:
    return Seance(
        plan_id=plan_id,
        week_start=seance.week_start,
        phase=seance.phase,
        detail=seance.detail,
        scheduled_date=seance.scheduled_date,
        seance_type=seance.seance_type,
        distance_meters=seance.distance_meters,
        theme=seance.theme,
        week_volume_meters=seance.week_volume_meters,
        status=seance.status,
        garmin_activity_id=seance.garmin_activity_id,
    )


class SqlAlchemyPlanRepository:
    """`plan.domain.PlanRepository` backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, plan: PlanRecord) -> PlanRecord:
        plan_row = Plan(objectif_id=plan.objectif_id, created_at=plan.created_at)
        self._session.add(plan_row)
        self._session.flush()

        seance_rows = [_seance_row(s, plan_row.id) for s in plan.seances]
        self._session.add_all(seance_rows)
        self._session.flush()

        return PlanRecord(
            id=plan_row.id,
            objectif_id=plan_row.objectif_id,
            created_at=plan_row.created_at,
            seances=[_to_seance(row) for row in seance_rows],
        )

    def get_active(self) -> PlanRecord | None:
        plan_stmt = select(Plan).order_by(Plan.created_at.desc(), Plan.id.desc()).limit(1)
        plan_row = self._session.execute(plan_stmt).scalar_one_or_none()
        if plan_row is None:
            return None

        seance_stmt = (
            select(Seance)
            .where(Seance.plan_id == plan_row.id)
            .order_by(Seance.week_start, Seance.scheduled_date)
        )
        seance_rows = self._session.execute(seance_stmt).scalars().all()

        return PlanRecord(
            id=plan_row.id,
            objectif_id=plan_row.objectif_id,
            created_at=plan_row.created_at,
            seances=[_to_seance(row) for row in seance_rows],
        )

    def update_seances(self, seances: list[SeanceRecord]) -> None:
        for seance in seances:
            stmt = (
                update(Seance)
                .where(Seance.id == seance.id)
                .values(
                    seance_type=seance.seance_type,
                    distance_meters=seance.distance_meters,
                    status=seance.status,
                    garmin_activity_id=seance.garmin_activity_id,
                )
            )
            self._session.execute(stmt)

    def replace_seances(
        self, removed_seance_ids: list[int], new_seances: list[SeanceRecord]
    ) -> list[SeanceRecord]:
        if removed_seance_ids:
            self._session.execute(delete(Seance).where(Seance.id.in_(removed_seance_ids)))

        rows = [_seance_row(s, s.plan_id) for s in new_seances if s.plan_id is not None]
        self._session.add_all(rows)
        self._session.flush()
        return [_to_seance(row) for row in rows]
