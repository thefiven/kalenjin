from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from garminconnect import Garmin
from garminconnect.exceptions import GarminConnectAuthenticationError

DEFAULT_PENDING_LOGIN_TTL_SECONDS = 5 * 60


class GarminAuthError(Exception):
    """Wraps every way a Garmin login attempt can fail — wrong credentials, a
    rejected MFA code, or an expired/unknown pending login — so no
    `garminconnect` exception type leaks past this module."""


@dataclass(frozen=True)
class GarminLoginSuccess:
    email: str
    password: str
    session_tokens: str


@dataclass(frozen=True)
class GarminMfaRequired:
    pending_login_id: str


GarminLoginOutcome = GarminLoginSuccess | GarminMfaRequired


@dataclass
class _PendingLogin:
    client: Garmin
    user_id: int
    email: str
    password: str
    expires_at: float


@dataclass
class PendingGarminLoginStore:
    """Bridges the two HTTP requests of a Garmin MFA login.

    `garminconnect`'s `resume_login` only works against the same in-memory `Garmin`
    instance that raised the MFA requirement — its session state (cookies, a
    partially completed SSO handshake) isn't serializable, so it can't be persisted
    to the DB or shared across processes. This store holds that live instance
    in-process between "submit password" and "submit MFA code", keyed by an opaque
    id, with a TTL so an abandoned login doesn't leak forever. This means MFA
    logins only complete against the worker process that started them — fine for a
    single-process deployment, a real constraint if Kalenjin ever runs multiple API
    replicas without sticky sessions.
    """

    ttl_seconds: float = DEFAULT_PENDING_LOGIN_TTL_SECONDS
    _pending: dict[str, _PendingLogin] = field(default_factory=dict)

    def put(self, client: Garmin, user_id: int, email: str, password: str) -> str:
        self._evict_expired()
        pending_login_id = str(uuid.uuid4())
        self._pending[pending_login_id] = _PendingLogin(
            client=client,
            user_id=user_id,
            email=email,
            password=password,
            expires_at=time.monotonic() + self.ttl_seconds,
        )
        return pending_login_id

    def pop(self, pending_login_id: str, user_id: int) -> _PendingLogin | None:
        self._evict_expired()
        pending = self._pending.pop(pending_login_id, None)
        if pending is None or pending.user_id != user_id:
            return None
        return pending

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [key for key, pending in self._pending.items() if pending.expires_at <= now]
        for key in expired:
            del self._pending[key]


def initiate_garmin_login(
    email: str, password: str, store: PendingGarminLoginStore, user_id: int
) -> GarminLoginOutcome:
    client = Garmin(email=email, password=password, return_on_mfa=True)
    try:
        mfa_status, _ = client.login()
    except GarminConnectAuthenticationError as exc:
        raise GarminAuthError(str(exc)) from exc

    if mfa_status == "needs_mfa":
        return GarminMfaRequired(store.put(client, user_id, email, password))
    return GarminLoginSuccess(email=email, password=password, session_tokens=client.client.dumps())


def complete_garmin_mfa(
    pending_login_id: str, mfa_code: str, store: PendingGarminLoginStore, user_id: int
) -> GarminLoginSuccess:
    pending = store.pop(pending_login_id, user_id)
    if pending is None:
        raise GarminAuthError(
            "No pending Garmin login found for this code — it may have expired. Start again."
        )
    try:
        pending.client.resume_login({}, mfa_code)
    except GarminConnectAuthenticationError as exc:
        raise GarminAuthError(str(exc)) from exc
    return GarminLoginSuccess(
        email=pending.email,
        password=pending.password,
        session_tokens=pending.client.client.dumps(),
    )
