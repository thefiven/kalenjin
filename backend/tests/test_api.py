from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from kalenjin.api import app, get_activity_repository, get_activity_source
from support.fakes import FakeRepository, raw_activity


class _AnyRangeSource:
    """Returns the same activities regardless of the requested date range —
    the endpoint test only cares about the final imported count, not chunking."""

    def __init__(self, raw_activities: list[dict[str, Any]]) -> None:
        self._raw_activities = raw_activities

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        return self._raw_activities


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sync_endpoint_reports_the_number_of_imported_activities() -> None:
    source = _AnyRangeSource([raw_activity("1")])
    repo = FakeRepository()

    app.dependency_overrides[get_activity_source] = lambda: source
    app.dependency_overrides[get_activity_repository] = lambda: repo
    try:
        client = TestClient(app)
        response = client.post("/sync")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"imported_count": 1}
