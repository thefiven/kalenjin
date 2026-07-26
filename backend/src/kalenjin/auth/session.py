from __future__ import annotations

from itsdangerous import BadSignature, URLSafeTimedSerializer

_SALT = "kalenjin-session"

DEFAULT_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days


class SessionCodec:
    """Signs and verifies the opaque session token stored in the browser's cookie.

    Wraps `itsdangerous` so no third-party type leaves this module."""

    def __init__(
        self, secret_key: str, max_age_seconds: int = DEFAULT_SESSION_MAX_AGE_SECONDS
    ) -> None:
        self._serializer = URLSafeTimedSerializer(secret_key, salt=_SALT)
        self._max_age_seconds = max_age_seconds

    def create(self, user_id: int) -> str:
        return self._serializer.dumps({"user_id": user_id})

    def verify(self, token: str) -> int | None:
        """The signed-in user's id, or `None` if `token` is missing, tampered,
        expired, or signed with a different key."""
        try:
            payload = self._serializer.loads(token, max_age=self._max_age_seconds)
        except BadSignature:
            return None
        user_id = payload.get("user_id")
        return user_id if isinstance(user_id, int) else None
