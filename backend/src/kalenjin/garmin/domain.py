from __future__ import annotations

from typing import Protocol, runtime_checkable

from kalenjin.plan.domain import GarminPushClient
from kalenjin.sync.domain import ActivitySource


@runtime_checkable
class GarminSessionClient(ActivitySource, GarminPushClient, Protocol):
    """A single authenticated Garmin Connect session that can both supply activity
    history and push/delete planned workouts — the two roles `GarminActivityClient`
    plays behind one login (issue #5's "reuse the auth from #1").

    Combining `sync.domain.ActivitySource` and `plan.domain.GarminPushClient` lets the
    DI layer depend on one typed thing instead of casting a narrower Protocol into a
    wider one at the call site. `@runtime_checkable` so a test can assert a fake
    genuinely satisfies both roles instead of only being caught by mypy (which this
    repo's CI doesn't run over `tests/`).
    """
