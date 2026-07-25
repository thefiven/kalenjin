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
    garmin_workout_id: str | None


def _live_scheduled_date(seance: SeanceRecord) -> date | None:
    """`scheduled_date` if `seance` is live — detailed and still pending — else `None`.

    The concept behind `is_upcoming_seance`/`is_past_due_seance`: a coarse week, or a
    séance already completed/skipped, is never live regardless of its date.
    """
    if seance.detail != "detailed" or seance.status != "pending":
        return None
    return seance.scheduled_date


def is_upcoming_seance(seance: SeanceRecord, today: date) -> bool:
    """A live séance scheduled today or later — still actionable enough to push to
    Garmin (`plan.push`) or adjust from a Rapport (`plan.adjustment`)."""
    scheduled_date = _live_scheduled_date(seance)
    return scheduled_date is not None and scheduled_date >= today


def is_past_due_seance(seance: SeanceRecord, today: date) -> bool:
    """A live séance scheduled before today — due to be matched against a realized
    activity by `plan.completion.match_completed_seances`."""
    scheduled_date = _live_scheduled_date(seance)
    return scheduled_date is not None and scheduled_date < today


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

    def commit(self) -> None:
        """Durably persist every write made on this repository so far, independent of
        whatever the rest of the ambient request does afterward.

        The request-scoped session otherwise commits (or rolls back) only once, at the
        very end — see `db.session.session_scope`. `plan.push.sync_plan_to_garmin`
        calls this after each successful Garmin push specifically so that a later
        push's failure, later in the same request, can't roll back an earlier one that
        already, genuinely happened on Garmin's side.
        """
        ...


class GarminPushClient(Protocol):
    """Boundary for pushing séances to Garmin Connect (issue #5), independent of the
    `python-garminconnect` SDK's own typed workout classes — no vendor type leaks past
    this Protocol, mirroring `llm.domain.LLMClient`'s ADR-0002 boundary.
    """

    def push_workout(self, seance: SeanceRecord, sport: str) -> str:
        """Uploads and schedules a workout for `seance`, returning the Garmin workout id."""
        ...

    def delete_workout(self, workout_id: str) -> None: ...
