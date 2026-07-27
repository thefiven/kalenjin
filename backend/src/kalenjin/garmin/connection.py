from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from garminconnect.exceptions import GarminConnectAuthenticationError

from kalenjin.auth.domain import UserRepository
from kalenjin.garmin.client import GarminActivityClient
from kalenjin.garmin.domain import GarminSessionClient
from kalenjin.garmin.login import (
    GarminLoginSuccess,
    PendingGarminLoginStore,
    complete_garmin_mfa,
    initiate_garmin_login,
)
from kalenjin.security.encryption import DecryptionError, decrypt, encrypt


class GarminNotConnectedError(Exception):
    """Raised by `session()` when the user has never connected a Garmin account."""


class GarminReauthRequiredError(Exception):
    """Raised by `session()` when the stored session can't be resumed — a rejected
    session (Garmin wants MFA again) and an undecryptable password (e.g. after an
    encryption-key rotation, ADR-0010) collapse into this one signal, since the
    remedy is identical either way: the user must go through `connect()` again."""


@dataclass(frozen=True)
class Connected:
    pass


@dataclass(frozen=True)
class MfaRequired:
    pending_login_id: str


GarminConnectOutcome = Connected | MfaRequired


class GarminConnection(Protocol):
    """This user's connection to Garmin (ADR-0006) — owns credential storage,
    decryption, the MFA-aware login state machine, session refresh, and disconnect,
    so callers never see ciphertext, an encryption key, or a `garminconnect` type."""

    def connect(self, email: str, password: str) -> GarminConnectOutcome:
        """Step 1 of self-service onboarding (issue #30). Raises `GarminAuthError` on
        a rejected login. Stores nothing on `MfaRequired` — `complete_mfa` finishes
        that case."""
        ...

    def complete_mfa(self, pending_login_id: str, mfa_code: str) -> GarminConnectOutcome:
        """Step 2, completing the login `connect` started. Raises `GarminAuthError` on
        an unknown/expired pending login or a rejected code."""
        ...

    def session(self) -> GarminSessionClient:
        """A ready-to-use, already-logged-in Garmin session for this user, refreshing
        and persisting the resumed session as a side effect. Raises
        `GarminNotConnectedError` if no account was ever connected, or
        `GarminReauthRequiredError` if the stored session can't be resumed."""
        ...

    def disconnect(self) -> None:
        """Clears stored credentials/session and purges this user's own in-flight
        pending MFA logins (issue #25 story 18). Idempotent."""
        ...


class UserGarminConnection:
    """`GarminConnection` backed by a real `UserRepository`, encryption key, and
    `PendingGarminLoginStore`."""

    def __init__(
        self,
        user_id: int,
        user_repo: UserRepository,
        encryption_key: str,
        pending_logins: PendingGarminLoginStore,
    ) -> None:
        self._user_id = user_id
        self._user_repo = user_repo
        self._encryption_key = encryption_key
        self._pending_logins = pending_logins

    def connect(self, email: str, password: str) -> GarminConnectOutcome:
        outcome = initiate_garmin_login(email, password, self._pending_logins, self._user_id)
        if isinstance(outcome, GarminLoginSuccess):
            self._store(outcome)
            return Connected()
        return MfaRequired(outcome.pending_login_id)

    def complete_mfa(self, pending_login_id: str, mfa_code: str) -> GarminConnectOutcome:
        outcome = complete_garmin_mfa(
            pending_login_id, mfa_code, self._pending_logins, self._user_id
        )
        self._store(outcome)
        return Connected()

    def _store(self, outcome: GarminLoginSuccess) -> None:
        key = self._encryption_key
        self._user_repo.set_garmin_credentials(
            self._user_id, outcome.email, encrypt(outcome.password, key)
        )
        self._user_repo.set_garmin_session(self._user_id, encrypt(outcome.session_tokens, key))

    def session(self) -> GarminSessionClient:
        user = self._user_repo.find_by_id(self._user_id)
        if user is None or user.garmin_email is None or user.garmin_password_encrypted is None:
            raise GarminNotConnectedError("Connect your Garmin account first")

        key = self._encryption_key
        try:
            password = decrypt(user.garmin_password_encrypted, key)
            session_tokens = (
                decrypt(user.garmin_session_encrypted, key)
                if user.garmin_session_encrypted
                else None
            )
        except DecryptionError as exc:
            raise GarminReauthRequiredError(
                "Your Garmin session needs to be reconnected — connect your account again"
            ) from exc

        client = GarminActivityClient(
            email=user.garmin_email, password=password, tokenstore=session_tokens or ""
        )
        try:
            client.login()
        except GarminConnectAuthenticationError as exc:
            raise GarminReauthRequiredError(
                "Your Garmin session needs to be reconnected — connect your account again"
            ) from exc

        self._user_repo.set_garmin_session(self._user_id, encrypt(client.dump_session(), key))
        return client

    def disconnect(self) -> None:
        self._user_repo.clear_garmin_credentials(self._user_id)
        self._pending_logins.purge_for_user(self._user_id)
