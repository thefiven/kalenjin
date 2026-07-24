from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from kalenjin.api import app


@contextmanager
def overriding_dependencies(
    overrides: dict[Callable[..., Any], Callable[..., Any]],
) -> Iterator[None]:
    """Temporarily set FastAPI dependency overrides, clearing them on exit
    regardless of test outcome."""
    app.dependency_overrides.update(overrides)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
