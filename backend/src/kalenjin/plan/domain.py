from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Protocol

SeanceDetail = Literal["coarse", "detailed"]

SeanceType = Literal["easy", "long_run", "tempo", "interval"]
SEANCE_TYPES: tuple[SeanceType, ...] = ("easy", "long_run", "tempo", "interval")
HARD_SEANCE_TYPES: frozenset[SeanceType] = frozenset({"tempo", "interval"})

SeanceStatus = Literal["pending", "completed", "skipped"]


@dataclass(frozen=True)
class ObjectifRecord:
    """A user-defined training goal. See CONTEXT.md's `Objectif` term."""

    id: int | None
    sport: str
    target_distance_meters: float
    target_date: date
    target_time_seconds: float | None
    created_at: datetime


@dataclass(frozen=True)
class SeanceRecord:
    """One entry in a `Plan`'s ordered sequence of séances (ADR-0001).

    Coarse entries (`detail="coarse"`) represent an entire week — `scheduled_date`,
    `seance_type`, and `distance_meters` are None, `theme` carries the week's plain-text
    summary. Detailed entries represent one concrete session — `theme` is None instead.
    """

    id: int | None
    plan_id: int | None
    week_start: date
    phase: str
    detail: SeanceDetail
    scheduled_date: date | None
    seance_type: SeanceType | None
    distance_meters: float | None
    theme: str | None
    week_volume_meters: float
    status: SeanceStatus
    garmin_activity_id: str | None


@dataclass(frozen=True)
class PlanRecord:
    id: int | None
    objectif_id: int
    created_at: datetime
    seances: list[SeanceRecord]


class ObjectifRepository(Protocol):
    """Persistence boundary for objectifs. Only one is ever active (see issue #4's scope)."""

    def save(self, objectif: ObjectifRecord) -> ObjectifRecord:
        """Persist `objectif`, returning it with its assigned id."""
        ...

    def get_active(self) -> ObjectifRecord | None:
        """The most recently created objectif, if any."""
        ...


class PlanRepository(Protocol):
    """Persistence boundary for plans and their séances."""

    def save(self, plan: PlanRecord) -> PlanRecord:
        """Persist `plan` and its séances, returning it with assigned ids."""
        ...

    def get_active(self) -> PlanRecord | None:
        """The plan for the active objectif, if any."""
        ...

    def update_seances(self, seances: list[SeanceRecord]) -> None:
        """Update existing séances in place (matched by id) — used by adjustment."""
        ...

    def replace_seances(
        self, removed_seance_ids: list[int], new_seances: list[SeanceRecord]
    ) -> list[SeanceRecord]:
        """Delete `removed_seance_ids` and insert `new_seances` — used by detailing/promotion.

        Returns `new_seances` with their assigned ids.
        """
        ...
