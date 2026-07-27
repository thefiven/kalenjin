from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from garminconnect.exceptions import GarminConnectAuthenticationError

from kalenjin.auth.domain import UserRecord
from kalenjin.garmin.connection import (
    Connected,
    GarminNotConnectedError,
    GarminReauthRequiredError,
    MfaRequired,
    UserGarminConnection,
)
from kalenjin.garmin.login import (
    GarminAuthError,
    GarminLoginSuccess,
    GarminMfaRequired,
    PendingGarminLoginStore,
)
from kalenjin.security.encryption import decrypt, encrypt
from support.fakes import FakeUserRepository

KEY = Fernet.generate_key().decode()


def _user(
    garmin_email: str | None = None,
    garmin_password_encrypted: str | None = None,
    garmin_session_encrypted: str | None = None,
) -> UserRecord:
    return UserRecord(
        id=1,
        google_subject="test-subject",
        email="friend@x.com",
        created_at=datetime.now(),
        garmin_email=garmin_email,
        garmin_password_encrypted=garmin_password_encrypted,
        garmin_session_encrypted=garmin_session_encrypted,
    )


def _connection(
    user_repo: FakeUserRepository, store: PendingGarminLoginStore | None = None
) -> UserGarminConnection:
    return UserGarminConnection(1, user_repo, KEY, store or PendingGarminLoginStore())


@patch("kalenjin.garmin.connection.initiate_garmin_login")
def test_connect_stores_credentials_and_session_encrypted_on_success(
    mock_initiate: MagicMock,
) -> None:
    mock_initiate.return_value = GarminLoginSuccess(
        email="runner@example.com", password="hunter2", session_tokens='{"di_token": "abc"}'
    )
    user_repo = FakeUserRepository(existing=[_user()])

    outcome = _connection(user_repo).connect("runner@example.com", "hunter2")

    assert outcome == Connected()
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.garmin_email == "runner@example.com"
    assert decrypt(stored.garmin_password_encrypted or "", KEY) == "hunter2"
    assert decrypt(stored.garmin_session_encrypted or "", KEY) == '{"di_token": "abc"}'


@patch("kalenjin.garmin.connection.initiate_garmin_login")
def test_connect_returns_mfa_required_and_stores_nothing(mock_initiate: MagicMock) -> None:
    mock_initiate.return_value = GarminMfaRequired(pending_login_id="pending-123")
    user_repo = FakeUserRepository(existing=[_user()])

    outcome = _connection(user_repo).connect("runner@example.com", "hunter2")

    assert outcome == MfaRequired(pending_login_id="pending-123")
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.garmin_email is None


@patch("kalenjin.garmin.connection.initiate_garmin_login")
def test_connect_with_bad_credentials_raises_and_stores_nothing(mock_initiate: MagicMock) -> None:
    mock_initiate.side_effect = GarminAuthError("bad credentials")
    user_repo = FakeUserRepository(existing=[_user()])

    with pytest.raises(GarminAuthError):
        _connection(user_repo).connect("runner@example.com", "wrong")

    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.garmin_email is None


@patch("kalenjin.garmin.connection.complete_garmin_mfa")
def test_complete_mfa_stores_credentials_and_session_on_success(mock_complete: MagicMock) -> None:
    mock_complete.return_value = GarminLoginSuccess(
        email="runner@example.com", password="hunter2", session_tokens='{"di_token": "abc"}'
    )
    user_repo = FakeUserRepository(existing=[_user()])

    outcome = _connection(user_repo).complete_mfa("pending-123", "000000")

    assert outcome == Connected()
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert decrypt(stored.garmin_password_encrypted or "", KEY) == "hunter2"


@patch("kalenjin.garmin.connection.complete_garmin_mfa")
def test_complete_mfa_with_an_unknown_pending_login_raises(mock_complete: MagicMock) -> None:
    mock_complete.side_effect = GarminAuthError("no such pending login")
    user_repo = FakeUserRepository(existing=[_user()])

    with pytest.raises(GarminAuthError):
        _connection(user_repo).complete_mfa("does-not-exist", "000000")


def test_session_raises_not_connected_when_no_credentials_are_stored() -> None:
    user_repo = FakeUserRepository(existing=[_user()])

    with pytest.raises(GarminNotConnectedError):
        _connection(user_repo).session()


def test_session_builds_a_client_from_the_users_decrypted_session_and_refreshes_it() -> None:
    user = _user(
        garmin_email="runner@example.com",
        garmin_password_encrypted=encrypt("hunter2", KEY),
        garmin_session_encrypted=encrypt('{"di_token": "abc"}', KEY),
    )
    user_repo = FakeUserRepository(existing=[user])

    with patch("kalenjin.garmin.connection.GarminActivityClient") as client_cls:
        client_cls.return_value.dump_session.return_value = '{"di_token": "refreshed"}'
        session = _connection(user_repo).session()

    assert session is client_cls.return_value
    client_cls.assert_called_once_with(
        email="runner@example.com", password="hunter2", tokenstore='{"di_token": "abc"}'
    )
    client_cls.return_value.login.assert_called_once_with()
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert decrypt(stored.garmin_session_encrypted or "", KEY) == '{"di_token": "refreshed"}'


def test_session_raises_reauth_required_when_garmin_rejects_the_resumed_session() -> None:
    user = _user(
        garmin_email="runner@example.com", garmin_password_encrypted=encrypt("hunter2", KEY)
    )
    user_repo = FakeUserRepository(existing=[user])

    with patch("kalenjin.garmin.connection.GarminActivityClient") as client_cls:
        client_cls.return_value.login.side_effect = GarminConnectAuthenticationError("needs mfa")
        with pytest.raises(GarminReauthRequiredError):
            _connection(user_repo).session()


def test_session_raises_reauth_required_when_the_stored_password_cannot_be_decrypted() -> None:
    wrong_key = Fernet.generate_key().decode()
    user = _user(
        garmin_email="runner@example.com", garmin_password_encrypted=encrypt("hunter2", wrong_key)
    )
    user_repo = FakeUserRepository(existing=[user])

    with pytest.raises(GarminReauthRequiredError):
        _connection(user_repo).session()


def test_disconnect_clears_credentials_and_purges_the_users_pending_logins() -> None:
    store = PendingGarminLoginStore()
    user = _user(
        garmin_email="runner@example.com",
        garmin_password_encrypted=encrypt("hunter2", KEY),
        garmin_session_encrypted=encrypt("{}", KEY),
    )
    user_repo = FakeUserRepository(existing=[user])
    connection = _connection(user_repo, store)
    with patch("kalenjin.garmin.connection.initiate_garmin_login") as mock_initiate:
        mock_initiate.return_value = GarminMfaRequired(pending_login_id="pending-123")
        connection.connect("runner@example.com", "hunter2")

    connection.disconnect()

    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.garmin_email is None
    assert stored.garmin_password_encrypted is None
    assert stored.garmin_session_encrypted is None
    assert store.pop("pending-123", user_id=1) is None


def test_disconnect_is_a_no_op_when_nothing_was_connected() -> None:
    user_repo = FakeUserRepository(existing=[_user()])

    _connection(user_repo).disconnect()  # must not raise
