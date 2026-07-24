from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, UniqueConstraint
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
