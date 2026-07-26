from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from kalenjin.api import app, get_current_user
from kalenjin.auth.domain import UserRecord

DEFAULT_TEST_USER = UserRecord(
    id=1,
    google_subject="test-google-subject",
    email="test@example.com",
    created_at=datetime(2024, 1, 1),
)


@contextmanager
def overriding_dependencies(
    overrides: dict[Callable[..., Any], Callable[..., Any]],
) -> Iterator[None]:
    """Temporarily set FastAPI dependency overrides, clearing them on exit
    regardless of test outcome.

    Every endpoint but `/health` now depends on `get_current_user` (ADR-0008), so this
    defaults it to a fake authenticated user — the many tests written before auth
    existed don't each need their own override. Pass an explicit `get_current_user`
    override to test unauthenticated or not-allowlisted behavior instead."""
    app.dependency_overrides.update({get_current_user: lambda: DEFAULT_TEST_USER, **overrides})
    try:
        yield
    finally:
        app.dependency_overrides.clear()
