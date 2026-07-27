from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from kalenjin.api import (
    OAUTH_STATE_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    app,
    get_auth_config,
    get_current_user,
    get_google_identity_verifier,
    get_session_codec,
    get_user_repository,
)
from kalenjin.auth.domain import GoogleIdentity, UserRecord
from kalenjin.auth.session import SessionCodec
from kalenjin.config.settings import AuthConfig
from support.api_client import overriding_dependencies
from support.fakes import FakeGoogleIdentityVerifier, FakeUserRepository

SESSION_CODEC = SessionCodec("test-session-secret")
FAKE_AUTH_CONFIG = AuthConfig(
    google_client_id="test-client-id",
    google_client_secret="test-client-secret",
    google_oauth_redirect_uri="http://localhost:8000/auth/google/callback",
    session_secret_key="test-session-secret",
    frontend_base_url="http://localhost:3000",
)


def _callback_overrides(
    verifier: FakeGoogleIdentityVerifier, user_repo: FakeUserRepository | None = None
) -> dict[Any, Any]:
    """Every `/auth/google/callback` dependency FastAPI resolves before the route body
    runs at all, even on an early-rejection path — so every test needs all four faked,
    not just the one its scenario cares about."""
    return {
        get_google_identity_verifier: lambda: verifier,
        get_user_repository: lambda: user_repo if user_repo is not None else FakeUserRepository(),
        get_session_codec: lambda: SESSION_CODEC,
        get_auth_config: lambda: FAKE_AUTH_CONFIG,
    }


def test_google_login_redirects_to_the_authorization_url_and_sets_a_state_cookie() -> None:
    with overriding_dependencies(
        {
            get_google_identity_verifier: lambda: FakeGoogleIdentityVerifier(),
            get_auth_config: lambda: FAKE_AUTH_CONFIG,
        }
    ):
        response = TestClient(app, follow_redirects=False).get("/auth/google/login")

    assert response.status_code in (302, 307)
    assert response.headers["location"].startswith("https://accounts.google.com/fake-consent?")
    assert OAUTH_STATE_COOKIE_NAME in response.cookies


def test_callback_creates_a_new_user_and_sets_a_session_cookie_for_an_allowlisted_email() -> None:
    verifier = FakeGoogleIdentityVerifier(GoogleIdentity(subject="sub-1", email="friend@x.com"))
    user_repo = FakeUserRepository(allowed_emails={"friend@x.com"})

    with overriding_dependencies(_callback_overrides(verifier, user_repo)):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(OAUTH_STATE_COOKIE_NAME, "expected-state")
        response = client.get(
            "/auth/google/callback", params={"code": "auth-code", "state": "expected-state"}
        )

    assert response.status_code in (302, 307)
    assert SESSION_COOKIE_NAME in response.cookies
    created = user_repo.find_by_google_subject("sub-1")
    assert created is not None
    assert created.email == "friend@x.com"


def test_callback_reuses_the_existing_user_on_a_second_login() -> None:
    verifier = FakeGoogleIdentityVerifier(GoogleIdentity(subject="sub-1", email="friend@x.com"))
    user_repo = FakeUserRepository(allowed_emails={"friend@x.com"})
    existing = user_repo.create("sub-1", "friend@x.com")

    with overriding_dependencies(_callback_overrides(verifier, user_repo)):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(OAUTH_STATE_COOKIE_NAME, "expected-state")
        client.get("/auth/google/callback", params={"code": "auth-code", "state": "expected-state"})

    found = user_repo.find_by_google_subject("sub-1")
    assert found is not None
    assert found.id == existing.id


def test_callback_rejects_a_google_account_not_on_the_allowlist() -> None:
    verifier = FakeGoogleIdentityVerifier(GoogleIdentity(subject="sub-1", email="stranger@x.com"))
    user_repo = FakeUserRepository(allowed_emails=set())

    with overriding_dependencies(_callback_overrides(verifier, user_repo)):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(OAUTH_STATE_COOKIE_NAME, "expected-state")
        response = client.get(
            "/auth/google/callback", params={"code": "auth-code", "state": "expected-state"}
        )

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "http://localhost:3000/login?error=not_invited"
    assert user_repo.find_by_google_subject("sub-1") is None


def test_callback_rejects_a_mismatched_state() -> None:
    verifier = FakeGoogleIdentityVerifier(GoogleIdentity(subject="sub-1", email="friend@x.com"))

    with overriding_dependencies(_callback_overrides(verifier)):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(OAUTH_STATE_COOKIE_NAME, "expected-state")
        response = client.get(
            "/auth/google/callback", params={"code": "auth-code", "state": "wrong-state"}
        )

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "http://localhost:3000/login?error=invalid_state"
    assert verifier.exchanged_codes == []


def test_callback_rejects_a_missing_state_cookie() -> None:
    verifier = FakeGoogleIdentityVerifier(GoogleIdentity(subject="sub-1", email="friend@x.com"))

    with overriding_dependencies(_callback_overrides(verifier)):
        response = TestClient(app, follow_redirects=False).get(
            "/auth/google/callback", params={"code": "auth-code", "state": "some-state"}
        )

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "http://localhost:3000/login?error=invalid_state"


def test_callback_redirects_to_login_with_an_error_when_google_rejects_the_code() -> None:
    verifier = FakeGoogleIdentityVerifier(identity=None)  # raises GoogleAuthError on exchange

    with overriding_dependencies(_callback_overrides(verifier)):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(OAUTH_STATE_COOKIE_NAME, "expected-state")
        response = client.get(
            "/auth/google/callback", params={"code": "bad-code", "state": "expected-state"}
        )

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "http://localhost:3000/login?error=google_auth_failed"


def test_logout_clears_the_session_cookie() -> None:
    client = TestClient(app)
    client.cookies.set(SESSION_COOKIE_NAME, "some-token")

    response = client.post("/auth/logout")

    assert response.status_code == 204
    set_cookie = response.headers.get("set-cookie", "")
    assert f'{SESSION_COOKIE_NAME}=""' in set_cookie
    assert "Max-Age=0" in set_cookie


def test_me_returns_the_current_users_email() -> None:
    fake_user = UserRecord(
        id=1, google_subject="sub-1", email="friend@x.com", created_at=datetime.now()
    )
    with overriding_dependencies({get_current_user: lambda: fake_user}):
        response = TestClient(app).get("/auth/me")

    assert response.status_code == 200
    assert response.json() == {"email": "friend@x.com"}


@pytest.mark.integration
def test_an_existing_endpoint_rejects_a_request_with_no_session_cookie() -> None:
    """The one test in this file that deliberately does NOT override `get_current_user`
    — it exercises the real gate end-to-end, so it needs `DbConfig`/`AuthConfig` to
    construct for real (CI sets the required env vars for this, same as
    `TEST_DATABASE_URL` already is)."""
    response = TestClient(app).get("/activities")

    assert response.status_code == 401


def test_get_current_user_rejects_a_session_for_a_revoked_user() -> None:
    """Issue #25 story 19: once the owner revokes a user's access, their
    already-issued session cookie must stop working on the very next request — no
    separate "is this session still valid" check exists beyond `find_by_id`.

    Deliberately doesn't use `overriding_dependencies`: that helper defaults
    `get_current_user` itself to a fake authenticated user, which would bypass the
    very gate this test exercises."""
    user_repo = FakeUserRepository(allowed_emails={"friend@x.com"})
    created = user_repo.create("sub-1", "friend@x.com")
    assert created.id is not None
    user_repo.revoke_access("friend@x.com")

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_codec] = lambda: SESSION_CODEC
    try:
        client = TestClient(app)
        client.cookies.set(SESSION_COOKIE_NAME, SESSION_CODEC.create(created.id))
        response = client.get("/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
