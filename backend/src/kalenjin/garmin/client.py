from __future__ import annotations

from datetime import date
from typing import Any, cast

from garminconnect import Garmin
from garminconnect.workout import CyclingWorkout

from kalenjin.garmin.workout_builder import build_workout
from kalenjin.plan.domain import SeanceRecord


class GarminActivityClient:
    """Adapter over `python-garminconnect` implementing `sync.domain.ActivitySource`.

    Resumes from `session` (a previously dumped, in-memory session — never a
    filesystem path; `garmin.connection.GarminConnection` owns persisting and
    decrypting it) when given, or does a credential login otherwise — though
    `session=None` isn't unconditionally a fresh login: the vendor's own
    `Garmin.login()` falls back to a `GARMINTOKENS` env var if set
    (`tokenstore = tokenstore or os.getenv("GARMINTOKENS")`), a Kalenjin never sets
    or documents. Deployments must not set `GARMINTOKENS`, or a "fresh" login could
    silently resume whatever tokenstore that path points to instead. Has no MFA
    capability of its own — that's exclusively `garmin/login.py`'s job, via the raw
    vendor client with `return_on_mfa=True`; a session this class can't resume (e.g.
    Garmin wants MFA again) surfaces as `GarminConnectAuthenticationError` from
    `login()`, for the caller to map to `GarminConnection`'s `GarminReauthRequiredError`.
    `garth` itself is not used directly — it's deprecated and can no longer perform a
    fresh login since Garmin changed its auth flow (see CONTEXT.md).
    """

    def __init__(self, email: str, password: str, session: str | None = None) -> None:
        self._session = session
        self._client = Garmin(email=email, password=password)

    def login(self) -> None:
        self._client.login(self._session)

    def dump_session(self) -> str:
        """The session's current tokens, serialized (`garminconnect`'s own
        `Client.dumps()`) — lets a caller persist a refreshed/resumed session for
        reuse, without writing to a tokenstore file on disk."""
        return cast(str, self._client.client.dumps())

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
