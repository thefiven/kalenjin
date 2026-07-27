import time
from unittest.mock import MagicMock, patch

import pytest
from garminconnect.exceptions import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from kalenjin.garmin.login import (
    GarminAuthError,
    GarminLoginSuccess,
    GarminMfaRequired,
    PendingGarminLoginStore,
    complete_garmin_mfa,
    initiate_garmin_login,
)


@patch("kalenjin.garmin.login.Garmin")
def test_a_clean_login_returns_success_with_the_dumped_session(garmin_cls: MagicMock) -> None:
    garmin_cls.return_value.login.return_value = (None, None)
    garmin_cls.return_value.client.dumps.return_value = '{"di_token": "abc"}'
    store = PendingGarminLoginStore()

    result = initiate_garmin_login("a@b.com", "secret", store, user_id=1)

    assert result == GarminLoginSuccess(
        email="a@b.com", password="secret", session_tokens='{"di_token": "abc"}'
    )
    garmin_cls.assert_called_once_with(email="a@b.com", password="secret", return_on_mfa=True)


@patch("kalenjin.garmin.login.Garmin")
def test_wrong_credentials_raise_a_garmin_auth_error_and_store_nothing(
    garmin_cls: MagicMock,
) -> None:
    garmin_cls.return_value.login.side_effect = GarminConnectAuthenticationError("bad creds")
    store = PendingGarminLoginStore()

    with pytest.raises(GarminAuthError):
        initiate_garmin_login("a@b.com", "wrong", store, user_id=1)

    assert store.pop("anything", user_id=1) is None


@patch("kalenjin.garmin.login.Garmin")
def test_mfa_required_returns_a_pending_login_id_without_a_session(
    garmin_cls: MagicMock,
) -> None:
    garmin_cls.return_value.login.return_value = ("needs_mfa", None)
    store = PendingGarminLoginStore()

    result = initiate_garmin_login("a@b.com", "secret", store, user_id=1)

    assert isinstance(result, GarminMfaRequired)
    assert result.pending_login_id


@patch("kalenjin.garmin.login.Garmin")
def test_completing_mfa_resumes_the_same_client_instance_and_returns_the_session(
    garmin_cls: MagicMock,
) -> None:
    garmin_cls.return_value.login.return_value = ("needs_mfa", None)
    garmin_cls.return_value.client.dumps.return_value = '{"di_token": "resumed"}'
    store = PendingGarminLoginStore()
    pending = initiate_garmin_login("a@b.com", "secret", store, user_id=1)
    assert isinstance(pending, GarminMfaRequired)

    result = complete_garmin_mfa(pending.pending_login_id, "123456", store, user_id=1)

    garmin_cls.return_value.resume_login.assert_called_once_with({}, "123456")
    assert result == GarminLoginSuccess(
        email="a@b.com", password="secret", session_tokens='{"di_token": "resumed"}'
    )


@patch("kalenjin.garmin.login.Garmin")
def test_completing_mfa_with_an_unknown_pending_login_id_raises(garmin_cls: MagicMock) -> None:
    store = PendingGarminLoginStore()

    with pytest.raises(GarminAuthError):
        complete_garmin_mfa("does-not-exist", "123456", store, user_id=1)


@patch("kalenjin.garmin.login.Garmin")
def test_completing_mfa_for_a_different_user_than_who_started_it_raises(
    garmin_cls: MagicMock,
) -> None:
    garmin_cls.return_value.login.return_value = ("needs_mfa", None)
    store = PendingGarminLoginStore()
    pending = initiate_garmin_login("a@b.com", "secret", store, user_id=1)
    assert isinstance(pending, GarminMfaRequired)

    with pytest.raises(GarminAuthError):
        complete_garmin_mfa(pending.pending_login_id, "123456", store, user_id=2)


@patch("kalenjin.garmin.login.Garmin")
def test_completing_mfa_with_a_wrong_code_raises_and_still_consumes_the_pending_login(
    garmin_cls: MagicMock,
) -> None:
    garmin_cls.return_value.login.return_value = ("needs_mfa", None)
    garmin_cls.return_value.resume_login.side_effect = GarminConnectAuthenticationError("bad code")
    store = PendingGarminLoginStore()
    pending = initiate_garmin_login("a@b.com", "secret", store, user_id=1)
    assert isinstance(pending, GarminMfaRequired)

    with pytest.raises(GarminAuthError):
        complete_garmin_mfa(pending.pending_login_id, "000000", store, user_id=1)

    # The pending login is consumed even on failure — retrying needs a fresh initiate.
    with pytest.raises(GarminAuthError):
        complete_garmin_mfa(pending.pending_login_id, "123456", store, user_id=1)


@patch("kalenjin.garmin.login.Garmin")
def test_being_rate_limited_by_garmin_raises_a_garmin_auth_error(garmin_cls: MagicMock) -> None:
    garmin_cls.return_value.login.side_effect = GarminConnectTooManyRequestsError("slow down")
    store = PendingGarminLoginStore()

    with pytest.raises(GarminAuthError):
        initiate_garmin_login("a@b.com", "secret", store, user_id=1)


@patch("kalenjin.garmin.login.Garmin")
def test_a_transport_failure_raises_a_garmin_auth_error(garmin_cls: MagicMock) -> None:
    garmin_cls.return_value.login.side_effect = GarminConnectConnectionError("network blip")
    store = PendingGarminLoginStore()

    with pytest.raises(GarminAuthError):
        initiate_garmin_login("a@b.com", "secret", store, user_id=1)


@patch("kalenjin.garmin.login.Garmin")
def test_purge_for_user_removes_only_that_users_pending_logins(garmin_cls: MagicMock) -> None:
    garmin_cls.return_value.login.return_value = ("needs_mfa", None)
    store = PendingGarminLoginStore()
    mine = initiate_garmin_login("a@b.com", "secret", store, user_id=1)
    theirs = initiate_garmin_login("c@d.com", "secret", store, user_id=2)
    assert isinstance(mine, GarminMfaRequired)
    assert isinstance(theirs, GarminMfaRequired)

    store.purge_for_user(1)

    assert store.pop(mine.pending_login_id, user_id=1) is None
    # A different user's pending login survives user 1's purge.
    garmin_cls.return_value.resume_login.return_value = None
    garmin_cls.return_value.client.dumps.return_value = "{}"
    assert complete_garmin_mfa(theirs.pending_login_id, "123456", store, user_id=2) is not None


@patch("kalenjin.garmin.login.Garmin")
def test_purge_for_user_is_a_no_op_when_the_user_has_no_pending_logins(
    garmin_cls: MagicMock,
) -> None:
    store = PendingGarminLoginStore()

    store.purge_for_user(1)  # must not raise


@patch("kalenjin.garmin.login.Garmin")
def test_an_expired_pending_login_cannot_be_resumed(garmin_cls: MagicMock) -> None:
    garmin_cls.return_value.login.return_value = ("needs_mfa", None)
    store = PendingGarminLoginStore(ttl_seconds=0.01)
    pending = initiate_garmin_login("a@b.com", "secret", store, user_id=1)
    assert isinstance(pending, GarminMfaRequired)
    time.sleep(0.02)

    with pytest.raises(GarminAuthError):
        complete_garmin_mfa(pending.pending_login_id, "123456", store, user_id=1)
