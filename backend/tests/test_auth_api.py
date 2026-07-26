from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from kalenjin.api import (
    OAUTH_STATE_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    app,
    get_current_user,
    get_google_identity_verifier,
    get_session_codec,
    get_user_repository,
)
from kalenjin.auth.domain import GoogleIdentity, UserRecord
from kalenjin.auth.session import SessionCodec
from support.api_client import overriding_dependencies
from support.fakes import FakeGoogleIdentityVerifier, FakeUserRepository

SESSION_CODEC = SessionCodec("test-session-secret")


def test_google_login_redirects_to_the_authorization_url_and_sets_a_state_cookie() -> None:
    with overriding_dependencies(
        {get_google_identity_verifier: lambda: FakeGoogleIdentityVerifier()}
    ):
        response = TestClient(app, follow_redirects=False).get("/auth/google/login")

    assert response.status_code in (302, 307)
    assert response.headers["location"].startswith("https://accounts.google.com/fake-consent?")
    assert OAUTH_STATE_COOKIE_NAME in response.cookies


def test_callback_creates_a_new_user_and_sets_a_session_cookie_for_an_allowlisted_email() -> None:
    verifier = FakeGoogleIdentityVerifier(GoogleIdentity(subject="sub-1", email="friend@x.com"))
    user_repo = FakeUserRepository(allowed_emails={"friend@x.com"})

    with overriding_dependencies(
        {
            get_google_identity_verifier: lambda: verifier,
            get_user_repository: lambda: user_repo,
            get_session_codec: lambda: SESSION_CODEC,
        }
    ):
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

    with overriding_dependencies(
        {
            get_google_identity_verifier: lambda: verifier,
            get_user_repository: lambda: user_repo,
            get_session_codec: lambda: SESSION_CODEC,
        }
    ):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(OAUTH_STATE_COOKIE_NAME, "expected-state")
        client.get("/auth/google/callback", params={"code": "auth-code", "state": "expected-state"})

    assert user_repo.find_by_google_subject("sub-1").id == existing.id


def test_callback_rejects_a_google_account_not_on_the_allowlist() -> None:
    verifier = FakeGoogleIdentityVerifier(GoogleIdentity(subject="sub-1", email="stranger@x.com"))
    user_repo = FakeUserRepository(allowed_emails=set())

    with overriding_dependencies(
        {get_google_identity_verifier: lambda: verifier, get_user_repository: lambda: user_repo}
    ):
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

    with overriding_dependencies({get_google_identity_verifier: lambda: verifier}):
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(OAUTH_STATE_COOKIE_NAME, "expected-state")
        response = client.get(
            "/auth/google/callback", params={"code": "auth-code", "state": "wrong-state"}
        )

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "http://localhost:3000/login?error=invalid_state"
    assert verifier.exchanged_codes == []


def test_callback_rejects_a_missing_state_cookie() -> None:
    with overriding_dependencies({}):
        response = TestClient(app, follow_redirects=False).get(
            "/auth/google/callback", params={"code": "auth-code", "state": "some-state"}
        )

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "http://localhost:3000/login?error=invalid_state"


def test_callback_redirects_to_login_with_an_error_when_google_rejects_the_code() -> None:
    verifier = FakeGoogleIdentityVerifier(identity=None)  # raises GoogleAuthError on exchange

    with overriding_dependencies({get_google_identity_verifier: lambda: verifier}):
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
    response = TestClient(app).get("/activities")

    assert response.status_code == 401
