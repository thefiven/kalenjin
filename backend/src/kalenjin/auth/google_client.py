from __future__ import annotations

from urllib.parse import urlencode

import httpx

from kalenjin.auth.domain import GoogleIdentity

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleAuthError(Exception):
    """Raised when Google's OAuth token exchange or identity lookup fails — a bad
    code, a revoked client, or a Google-side error. No `httpx`-specific type leaves
    this module."""


class GoogleOAuthClient:
    """`auth.domain.GoogleIdentityVerifier` backed by Google's OAuth2/OpenID Connect
    endpoints (ADR-0008)."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = httpx.Client()

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> GoogleIdentity:
        token_response = self._http.post(
            _TOKEN_URL,
            data={
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_response.status_code != 200:
            raise GoogleAuthError(f"Google token exchange failed: {token_response.status_code}")
        access_token = token_response.json()["access_token"]

        userinfo_response = self._http.get(
            _USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_response.status_code != 200:
            raise GoogleAuthError(f"Google userinfo lookup failed: {userinfo_response.status_code}")
        payload = userinfo_response.json()
        return GoogleIdentity(subject=payload["sub"], email=payload["email"])
