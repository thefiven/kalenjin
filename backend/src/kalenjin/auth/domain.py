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
    """

    id: int | None
    google_subject: str
    email: str
    created_at: datetime
    gemini_api_key_encrypted: str | None = None


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

    def find_by_google_subject(self, subject: str) -> UserRecord | None: ...

    def find_by_id(self, user_id: int) -> UserRecord | None: ...

    def create(self, subject: str, email: str) -> UserRecord:
        """Creates a new `User` row. Callers must have already checked
        `is_email_allowed`."""
        ...

    def set_gemini_api_key(self, user_id: int, encrypted_key: str) -> None:
        """Stores (or replaces, on rotation) the user's encrypted Gemini API key
        (issue #29). Callers encrypt before calling — this repository only persists
        ciphertext."""
        ...
