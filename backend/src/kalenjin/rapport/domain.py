from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

PerceivedEffort = Literal["low", "as_expected", "high"]
PERCEIVED_EFFORTS: tuple[PerceivedEffort, ...] = ("low", "as_expected", "high")

RapportFlag = Literal["none", "pain", "illness", "missed_session"]
RAPPORT_FLAGS: tuple[RapportFlag, ...] = ("none", "pain", "illness", "missed_session")


@dataclass(frozen=True)
class RapportRecord:
    """An AI-generated post-session analysis. See CONTEXT.md's `Rapport` term.

    `completed_as_planned`/`perceived_effort`/`flag` are a structured signal (distinct from
    the free-text `strengths`/`improvements`) that plan adjustment (ticket #4) consumes
    without having to re-interpret prose.
    """

    garmin_activity_id: str
    strengths: str
    improvements: str
    generated_at: datetime
    completed_as_planned: bool
    perceived_effort: PerceivedEffort
    flag: RapportFlag


class RapportRepository(Protocol):
    """Persistence boundary for rapports, independent of any specific database."""

    def save(self, rapport: RapportRecord) -> None:
        """Persist a rapport, replacing any existing one for the same activity."""
        ...

    def get_for_activity(self, garmin_activity_id: str) -> RapportRecord | None: ...

    def list_recent(self, limit: int) -> list[RapportRecord]:
        """The most recently generated rapports, most-recent-first.

        Feeds plan adjustment's consecutive-high-effort check (see `plan/adjustment.py`).
        """
        ...
