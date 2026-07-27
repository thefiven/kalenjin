from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from garminconnect.exceptions import GarminConnectAuthenticationError

from kalenjin.api import (
    app,
    get_activity_source,
    get_current_user,
    get_encryption_config,
    get_user_repository,
)
from kalenjin.auth.domain import UserRecord
from kalenjin.config.settings import EncryptionConfig
from kalenjin.garmin.login import GarminAuthError, GarminLoginSuccess, GarminMfaRequired
from kalenjin.security.encryption import decrypt, encrypt
from support.api_client import overriding_dependencies
from support.fakes import FakeUserRepository

TEST_ENCRYPTION_CONFIG = EncryptionConfig(secret_encryption_key=Fernet.generate_key().decode())


def _fake_user(
    user_id: int = 1,
    garmin_email: str | None = None,
    garmin_password_encrypted: str | None = None,
    garmin_session_encrypted: str | None = None,
) -> UserRecord:
    return UserRecord(
        id=user_id,
        google_subject="test-subject",
        email="friend@x.com",
        created_at=datetime.now(),
        garmin_email=garmin_email,
        garmin_password_encrypted=garmin_password_encrypted,
        garmin_session_encrypted=garmin_session_encrypted,
    )


@patch("kalenjin.api.initiate_garmin_login")
def test_a_clean_login_stores_credentials_and_session_encrypted(mock_initiate: MagicMock) -> None:
    mock_initiate.return_value = GarminLoginSuccess(
        email="runner@example.com", password="hunter2", session_tokens='{"di_token": "abc"}'
    )
    user_repo = FakeUserRepository(existing=[_fake_user()])

    with overriding_dependencies(
        {
            get_current_user: lambda: _fake_user(),
            get_user_repository: lambda: user_repo,
            get_encryption_config: lambda: TEST_ENCRYPTION_CONFIG,
        }
    ):
        response = TestClient(app).post(
            "/users/me/garmin-credentials",
            json={"email": "runner@example.com", "password": "hunter2"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "connected", "pending_login_id": None}
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.garmin_email == "runner@example.com"
    assert stored.garmin_password_encrypted is not None
    assert (
        decrypt(stored.garmin_password_encrypted, TEST_ENCRYPTION_CONFIG.secret_encryption_key)
        == "hunter2"
    )
    assert stored.garmin_session_encrypted is not None
    assert (
        decrypt(stored.garmin_session_encrypted, TEST_ENCRYPTION_CONFIG.secret_encryption_key)
        == '{"di_token": "abc"}'
    )


@patch("kalenjin.api.initiate_garmin_login")
def test_mfa_required_returns_a_pending_login_id_and_stores_nothing(
    mock_initiate: MagicMock,
) -> None:
    mock_initiate.return_value = GarminMfaRequired(pending_login_id="pending-123")
    user_repo = FakeUserRepository(existing=[_fake_user()])

    with overriding_dependencies(
        {
            get_current_user: lambda: _fake_user(),
            get_user_repository: lambda: user_repo,
            get_encryption_config: lambda: TEST_ENCRYPTION_CONFIG,
        }
    ):
        response = TestClient(app).post(
            "/users/me/garmin-credentials",
            json={"email": "runner@example.com", "password": "hunter2"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "mfa_required", "pending_login_id": "pending-123"}
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.garmin_email is None
    assert stored.garmin_password_encrypted is None


@patch("kalenjin.api.initiate_garmin_login")
def test_invalid_credentials_are_rejected_and_store_nothing(mock_initiate: MagicMock) -> None:
    mock_initiate.side_effect = GarminAuthError("bad credentials")
    user_repo = FakeUserRepository(existing=[_fake_user()])

    with overriding_dependencies(
        {
            get_current_user: lambda: _fake_user(),
            get_user_repository: lambda: user_repo,
            get_encryption_config: lambda: TEST_ENCRYPTION_CONFIG,
        }
    ):
        response = TestClient(app).post(
            "/users/me/garmin-credentials",
            json={"email": "runner@example.com", "password": "wrong"},
        )

    assert response.status_code == 400
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.garmin_email is None


@patch("kalenjin.api.complete_garmin_mfa")
def test_completing_mfa_stores_credentials_and_session(mock_complete: MagicMock) -> None:
    mock_complete.return_value = GarminLoginSuccess(
        email="runner@example.com", password="hunter2", session_tokens='{"di_token": "resumed"}'
    )
    user_repo = FakeUserRepository(existing=[_fake_user()])

    with overriding_dependencies(
        {
            get_current_user: lambda: _fake_user(),
            get_user_repository: lambda: user_repo,
            get_encryption_config: lambda: TEST_ENCRYPTION_CONFIG,
        }
    ):
        response = TestClient(app).post(
            "/users/me/garmin-credentials/mfa",
            json={"pending_login_id": "pending-123", "mfa_code": "123456"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "connected"
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.garmin_email == "runner@example.com"


@patch("kalenjin.api.complete_garmin_mfa")
def test_completing_mfa_with_an_expired_pending_login_is_rejected(
    mock_complete: MagicMock,
) -> None:
    mock_complete.side_effect = GarminAuthError("expired")
    user_repo = FakeUserRepository(existing=[_fake_user()])

    with overriding_dependencies(
        {
            get_current_user: lambda: _fake_user(),
            get_user_repository: lambda: user_repo,
            get_encryption_config: lambda: TEST_ENCRYPTION_CONFIG,
        }
    ):
        response = TestClient(app).post(
            "/users/me/garmin-credentials/mfa",
            json={"pending_login_id": "does-not-exist", "mfa_code": "123456"},
        )

    assert response.status_code == 400


def test_get_activity_source_rejects_a_user_without_connected_garmin_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_activity_source(
            user=_fake_user(),
            user_repo=FakeUserRepository(existing=[_fake_user()]),
            encryption_config=TEST_ENCRYPTION_CONFIG,
        )

    assert exc_info.value.status_code == 400


def test_get_activity_source_builds_a_client_from_the_users_decrypted_session() -> None:
    key = TEST_ENCRYPTION_CONFIG.secret_encryption_key
    user = _fake_user(
        garmin_email="runner@example.com",
        garmin_password_encrypted=encrypt("hunter2", key),
        garmin_session_encrypted=encrypt('{"di_token": "abc"}', key),
    )
    user_repo = FakeUserRepository(existing=[user])

    with patch("kalenjin.api.GarminActivityClient") as client_cls:
        client_cls.return_value.dump_session.return_value = '{"di_token": "refreshed"}'
        get_activity_source(
            user=user, user_repo=user_repo, encryption_config=TEST_ENCRYPTION_CONFIG
        )

    client_cls.assert_called_once_with(
        email="runner@example.com", password="hunter2", tokenstore='{"di_token": "abc"}'
    )
    client_cls.return_value.login.assert_called_once_with()
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert decrypt(stored.garmin_session_encrypted or "", key) == '{"di_token": "refreshed"}'


def test_get_activity_source_surfaces_a_clear_error_when_mfa_is_required_again() -> None:
    key = TEST_ENCRYPTION_CONFIG.secret_encryption_key
    user = _fake_user(
        garmin_email="runner@example.com", garmin_password_encrypted=encrypt("hunter2", key)
    )
    user_repo = FakeUserRepository(existing=[user])

    with patch("kalenjin.api.GarminActivityClient") as client_cls:
        client_cls.return_value.login.side_effect = GarminConnectAuthenticationError(
            "MFA Required but no prompt_mfa mechanism supplied"
        )
        with pytest.raises(HTTPException) as exc_info:
            get_activity_source(
                user=user, user_repo=user_repo, encryption_config=TEST_ENCRYPTION_CONFIG
            )

    assert exc_info.value.status_code == 400


def test_disconnect_garmin_account_clears_email_password_and_session() -> None:
    key = TEST_ENCRYPTION_CONFIG.secret_encryption_key
    user = _fake_user(
        garmin_email="runner@example.com",
        garmin_password_encrypted=encrypt("hunter2", key),
        garmin_session_encrypted=encrypt('{"di_token": "abc"}', key),
    )
    user_repo = FakeUserRepository(existing=[user])

    with overriding_dependencies(
        {get_current_user: lambda: user, get_user_repository: lambda: user_repo}
    ):
        response = TestClient(app).delete("/users/me/garmin-credentials")

    assert response.status_code == 204
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.garmin_email is None
    assert stored.garmin_password_encrypted is None
    assert stored.garmin_session_encrypted is None


def test_disconnect_garmin_account_is_a_204_when_nothing_was_connected() -> None:
    user_repo = FakeUserRepository(existing=[_fake_user()])

    with overriding_dependencies(
        {get_current_user: lambda: _fake_user(), get_user_repository: lambda: user_repo}
    ):
        response = TestClient(app).delete("/users/me/garmin-credentials")

    assert response.status_code == 204
