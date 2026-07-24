from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any, cast

from garminconnect import Garmin


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
