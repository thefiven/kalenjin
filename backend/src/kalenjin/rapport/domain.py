from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class RapportRecord:
    """An AI-generated post-session analysis. See CONTEXT.md's `Rapport` term."""

    garmin_activity_id: str
    strengths: str
    improvements: str
    generated_at: datetime


class RapportRepository(Protocol):
    """Persistence boundary for rapports, independent of any specific database."""

    def save(self, rapport: RapportRecord) -> None:
        """Persist a rapport, replacing any existing one for the same activity."""
        ...

    def get_for_activity(self, garmin_activity_id: str) -> RapportRecord | None: ...
