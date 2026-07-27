from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class GoogleIdentity:
    """The identity Google vouches for after a completed OAuth code exchange."""

    subject: str
    email: str


class GoogleIdentityVerifier(Protocol):
    """Boundary over Google's OAuth code exchange, independent of the HTTP calls
    involved — no Google-specific type leaks past this Protocol (mirrors
    `llm.domain.LLMClient`'s ADR-0002 boundary)."""

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        """The URL to send the browser to start the Google consent screen."""
        ...

    def exchange_code(self, code: str, redirect_uri: str) -> GoogleIdentity:
        """Exchanges an OAuth authorization code for the identity Google returns."""
        ...


@dataclass(frozen=True)
class UserRecord:
    """A Kalenjin account — one per invited person (ADR-0008).

    `gemini_api_key_encrypted` is the user's own Gemini API key (issue #29), stored
    encrypted (ADR-0010) — `None` until they've connected one. Still ciphertext here;
    callers decrypt it themselves with `security.encryption`, which needs the
    encryption key that isn't this record's concern.

    `garmin_email`/`garmin_password_encrypted` are the user's own Garmin credentials
    (issue #30, ADR-0006) — `python-garminconnect` has no OAuth, so this is the real
    login the user typed, encrypted at rest. `garmin_session_encrypted` is the
    resumable session `garminconnect` produced from that login (its own
    `Client.dumps()` JSON, also encrypted) — reusing it on sync lets a user's session
    survive without a fresh password login (and possible repeat MFA) every time.
    """

    id: int | None
    google_subject: str
    email: str
    created_at: datetime
    gemini_api_key_encrypted: str | None = None
    garmin_email: str | None = None
    garmin_password_encrypted: str | None = None
    garmin_session_encrypted: str | None = None
    is_active: bool = True


class UserRepository(Protocol):
    """Persistence boundary for users and the invite allowlist that gates account
    creation (ADR-0008)."""

    def is_email_allowed(self, email: str) -> bool:
        """Whether `email` is on the invite allowlist — checked before a `User` is
        ever created for it."""
        ...

    def add_to_allowlist(self, email: str) -> None:
        """Adds `email` to the invite allowlist. Idempotent — re-adding an already
        allowlisted email is a no-op."""
        ...

    def revoke_access(self, email: str) -> None:
        """Cuts off `email`'s access (issue #25 story 19): removes it from the invite
        allowlist, so no future Google login for it can create or resume a `User`, and
        deactivates any existing `User` row for it, so `find_by_id` stops returning it —
        the next request on an already-issued session cookie hits `get_current_user`'s
        401 path. Idempotent; safe to call whether or not a `User` row exists yet."""
        ...

    def find_by_google_subject(self, subject: str) -> UserRecord | None: ...

    def find_by_id(self, user_id: int) -> UserRecord | None:
        """`None` both when no such row exists and when the matching row has been
        deactivated by `revoke_access` — callers (`get_current_user`) treat both the
        same way, as "not a usable session"."""
        ...

    def create(self, subject: str, email: str) -> UserRecord:
        """Creates a new `User` row. Callers must have already checked
        `is_email_allowed`."""
        ...

    def set_gemini_api_key(self, user_id: int, encrypted_key: str) -> None:
        """Stores (or replaces, on rotation) the user's encrypted Gemini API key
        (issue #29). Callers encrypt before calling — this repository only persists
        ciphertext."""
        ...

    def set_garmin_credentials(self, user_id: int, email: str, encrypted_password: str) -> None:
        """Stores (or replaces, e.g. after a Garmin password change) the user's Garmin
        email and encrypted password (issue #30). Callers encrypt before calling —
        this repository only persists ciphertext."""
        ...

    def set_garmin_session(self, user_id: int, encrypted_session: str) -> None:
        """Stores (or replaces) the user's resumable Garmin session tokens (issue
        #30), produced by a successful login or MFA completion. Callers encrypt
        before calling — this repository only persists ciphertext."""
        ...

    def clear_garmin_credentials(self, user_id: int) -> None:
        """Disconnects the user's Garmin account (issue #25 story 18): clears the
        stored email, encrypted password, and encrypted session, so sync stops (the
        next attempt hits the same "connect your Garmin account first" path as a user
        who never connected one). Idempotent."""
        ...
