from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Activity(Base):
    """A realized Garmin activity, imported or synced. See CONTEXT.md's `Sport` and `Séance` terms.

    `raw_payload` keeps Garmin's full response so future metrics can be surfaced
    without a migration every time a new field turns out to matter.
    """

    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("garmin_activity_id", name="uq_activities_garmin_activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    garmin_activity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sport: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, index=True
    )
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class Rapport(Base):
    """An AI-generated post-session analysis for an `Activity`. See CONTEXT.md's `Rapport` term."""

    __tablename__ = "rapports"
    __table_args__ = (
        UniqueConstraint("garmin_activity_id", name="uq_rapports_garmin_activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    garmin_activity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strengths: Mapped[str] = mapped_column(String, nullable=False)
    improvements: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    completed_as_planned: Mapped[bool] = mapped_column(Boolean, nullable=False)
    perceived_effort: Mapped[str] = mapped_column(String, nullable=False)
    flag: Mapped[str] = mapped_column(String, nullable=False)


class Objectif(Base):
    """A user-defined training goal. See CONTEXT.md's `Objectif` term.

    Only one objectif is ever active at a time (issue #4's scope) — `get_active`
    returns the most recently created row rather than there being an `is_active` flag.
    """

    __tablename__ = "objectifs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sport: Mapped[str] = mapped_column(String, nullable=False)
    target_distance_meters: Mapped[float] = mapped_column(Float, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class Plan(Base):
    """The séance sequence generated for an `Objectif`. See CONTEXT.md's `Plan` term."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    objectif_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("objectifs.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class Seance(Base):
    """One entry — coarse (a week) or detailed (a concrete session) — in a `Plan`."""

    __tablename__ = "seances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plans.id"), nullable=False, index=True
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(String, nullable=False)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    seance_type: Mapped[str | None] = mapped_column(String, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    theme: Mapped[str | None] = mapped_column(String, nullable=True)
    week_volume_meters: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    garmin_activity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    garmin_workout_id: Mapped[str | None] = mapped_column(String, nullable=True)
