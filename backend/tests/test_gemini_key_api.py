from fastapi.testclient import TestClient

from kalenjin.api import (
    app,
    get_activity_repository,
    get_gemini_connection,
    get_objectif_repository,
    get_plan_repository,
)
from kalenjin.llm.connection import GeminiInvalidKeyError
from support.api_client import overriding_dependencies
from support.fakes import (
    FakeGeminiConnection,
    FakeObjectifRepository,
    FakePlanRepository,
    FakeRepository,
)

# Thin HTTP-wiring tests: does each route call the right `GeminiConnection` method and
# map its outcome to the right response/status code? Key validation and decryption
# live in `llm/connection.py`, tested directly against the real implementation in
# tests/llm/test_gemini_connection.py.


def test_set_gemini_api_key_returns_204_and_forwards_the_key() -> None:
    connection = FakeGeminiConnection()

    with overriding_dependencies({get_gemini_connection: lambda: connection}):
        response = TestClient(app).post("/users/me/gemini-key", json={"api_key": "my-real-key"})

    assert response.status_code == 204
    assert connection.set_keys == ["my-real-key"]


def test_set_gemini_api_key_rejects_an_invalid_key_with_a_400() -> None:
    connection = FakeGeminiConnection(set_key_error=GeminiInvalidKeyError("Invalid Gemini API key"))

    with overriding_dependencies({get_gemini_connection: lambda: connection}):
        response = TestClient(app).post("/users/me/gemini-key", json={"api_key": "bad-key"})

    assert response.status_code == 400


def test_create_objectif_returns_a_clear_error_when_gemini_is_not_connected() -> None:
    with overriding_dependencies(
        {
            get_gemini_connection: lambda: FakeGeminiConnection(),
            get_activity_repository: lambda: FakeRepository(),
            get_objectif_repository: lambda: FakeObjectifRepository(),
            get_plan_repository: lambda: FakePlanRepository(),
        }
    ):
        response = TestClient(app).post(
            "/objectif",
            json={
                "sport": "running",
                "target_distance_meters": 10_000,
                "target_date": "2026-12-01",
            },
        )

    assert response.status_code == 400
