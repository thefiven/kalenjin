from unittest.mock import MagicMock, patch

import pytest

from kalenjin.auth.domain import GoogleIdentity
from kalenjin.auth.google_client import GoogleAuthError, GoogleOAuthClient


def test_authorization_url_includes_the_client_id_redirect_uri_and_state() -> None:
    client = GoogleOAuthClient(client_id="cid", client_secret="secret")

    url = client.authorization_url("http://localhost:3000/callback", state="xyz")

    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=cid" in url
    assert "state=xyz" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback" in url


@patch("kalenjin.auth.google_client.httpx.Client")
def test_exchange_code_returns_the_identity_from_userinfo(http_client_cls: MagicMock) -> None:
    http_client = http_client_cls.return_value
    http_client.post.return_value = MagicMock(status_code=200, json=lambda: {"access_token": "tok"})
    http_client.get.return_value = MagicMock(
        status_code=200, json=lambda: {"sub": "123", "email": "friend@example.com"}
    )
    client = GoogleOAuthClient(client_id="cid", client_secret="secret")

    identity = client.exchange_code("auth-code", "http://localhost:3000/callback")

    http_client.post.assert_called_once_with(
        "https://oauth2.googleapis.com/token",
        data={
            "code": "auth-code",
            "client_id": "cid",
            "client_secret": "secret",
            "redirect_uri": "http://localhost:3000/callback",
            "grant_type": "authorization_code",
        },
    )
    http_client.get.assert_called_once_with(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": "Bearer tok"},
    )
    assert identity == GoogleIdentity(subject="123", email="friend@example.com")


@patch("kalenjin.auth.google_client.httpx.Client")
def test_exchange_code_raises_when_the_token_exchange_fails(http_client_cls: MagicMock) -> None:
    http_client = http_client_cls.return_value
    http_client.post.return_value = MagicMock(status_code=400)
    client = GoogleOAuthClient(client_id="cid", client_secret="secret")

    with pytest.raises(GoogleAuthError):
        client.exchange_code("bad-code", "http://localhost:3000/callback")


@patch("kalenjin.auth.google_client.httpx.Client")
def test_exchange_code_raises_when_the_userinfo_lookup_fails(http_client_cls: MagicMock) -> None:
    http_client = http_client_cls.return_value
    http_client.post.return_value = MagicMock(status_code=200, json=lambda: {"access_token": "tok"})
    http_client.get.return_value = MagicMock(status_code=401)
    client = GoogleOAuthClient(client_id="cid", client_secret="secret")

    with pytest.raises(GoogleAuthError):
        client.exchange_code("auth-code", "http://localhost:3000/callback")
