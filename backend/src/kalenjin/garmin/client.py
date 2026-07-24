from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any, cast

from garminconnect import Garmin
from garminconnect.workout import CyclingWorkout

from kalenjin.garmin.workout_builder import build_workout
from kalenjin.plan.domain import SeanceRecord


class GarminActivityClient:
    """Adapter over `python-garminconnect` implementing `sync.domain.ActivitySource`.

    Uses `garminconnect`'s own tokenstore-based login: it loads a cached session
    from `tokenstore` when present, and falls back to a fresh credential login,
    persisting the new session there for next time. `garth` itself is not used
    directly — it's deprecated and can no longer perform a fresh login since
    Garmin changed its auth flow (see CONTEXT.md).
    """

    def __init__(
        self,
        email: str,
        password: str,
        tokenstore: str,
        prompt_mfa: Callable[[], str] | None = None,
    ) -> None:
        self._tokenstore = tokenstore
        self._client = Garmin(email=email, password=password, prompt_mfa=prompt_mfa)

    def login(self) -> None:
        self._client.login(self._tokenstore)

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self._client.get_activities_by_date(start_date.isoformat(), end_date.isoformat()),
        )

    def push_workout(self, seance: SeanceRecord, sport: str) -> str:
        """Implements `plan.domain.GarminPushClient` (issue #5)."""
        if seance.scheduled_date is None:
            raise ValueError("Cannot push a séance with no scheduled_date")

        workout = build_workout(seance, sport)
        upload = (
            self._client.upload_cycling_workout(workout)
            if isinstance(workout, CyclingWorkout)
            else self._client.upload_running_workout(workout)
        )
        workout_id = str(upload["workoutId"])
        self._client.schedule_workout(workout_id, seance.scheduled_date.isoformat())
        return workout_id

    def delete_workout(self, workout_id: str) -> None:
        """Implements `plan.domain.GarminPushClient` (issue #5)."""
        self._client.delete_workout(workout_id)
