from fastapi.testclient import TestClient

from kalenjin.api import app, get_garmin_connection
from kalenjin.garmin.connection import Connected, MfaRequired
from kalenjin.garmin.login import GarminAuthError
from support.api_client import overriding_dependencies
from support.fakes import FakeGarminConnection

# Thin HTTP-wiring tests: does each route call the right `GarminConnection` method and
# map its outcome to the right response/status code? The MFA state machine, decryption,
# and session refresh live in `garmin/connection.py`, tested directly against the real
# implementation in tests/garmin/test_garmin_connection.py.


def test_connect_returns_connected_when_the_login_succeeds() -> None:
    connection = FakeGarminConnection(connect_result=Connected())

    with overriding_dependencies({get_garmin_connection: lambda: connection}):
        response = TestClient(app).post(
            "/users/me/garmin-credentials",
            json={"email": "runner@example.com", "password": "hunter2"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "connected", "pending_login_id": None}


def test_connect_returns_mfa_required_with_the_pending_login_id() -> None:
    connection = FakeGarminConnection(connect_result=MfaRequired(pending_login_id="pending-123"))

    with overriding_dependencies({get_garmin_connection: lambda: connection}):
        response = TestClient(app).post(
            "/users/me/garmin-credentials",
            json={"email": "runner@example.com", "password": "hunter2"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "mfa_required", "pending_login_id": "pending-123"}


def test_connect_rejects_invalid_credentials_with_a_400() -> None:
    connection = FakeGarminConnection(connect_result=GarminAuthError("bad credentials"))

    with overriding_dependencies({get_garmin_connection: lambda: connection}):
        response = TestClient(app).post(
            "/users/me/garmin-credentials",
            json={"email": "runner@example.com", "password": "wrong"},
        )

    assert response.status_code == 400


def test_complete_mfa_returns_connected_on_success() -> None:
    connection = FakeGarminConnection(complete_mfa_result=Connected())

    with overriding_dependencies({get_garmin_connection: lambda: connection}):
        response = TestClient(app).post(
            "/users/me/garmin-credentials/mfa",
            json={"pending_login_id": "pending-123", "mfa_code": "123456"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "connected"


def test_complete_mfa_with_an_expired_pending_login_returns_a_400() -> None:
    connection = FakeGarminConnection(complete_mfa_result=GarminAuthError("expired"))

    with overriding_dependencies({get_garmin_connection: lambda: connection}):
        response = TestClient(app).post(
            "/users/me/garmin-credentials/mfa",
            json={"pending_login_id": "does-not-exist", "mfa_code": "123456"},
        )

    assert response.status_code == 400


def test_disconnect_calls_disconnect_and_returns_204() -> None:
    connection = FakeGarminConnection()

    with overriding_dependencies({get_garmin_connection: lambda: connection}):
        response = TestClient(app).delete("/users/me/garmin-credentials")

    assert response.status_code == 204
    assert connection.disconnected is True
