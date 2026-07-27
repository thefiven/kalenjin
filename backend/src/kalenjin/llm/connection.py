from __future__ import annotations

from typing import Protocol

from kalenjin.auth.domain import UserRepository
from kalenjin.llm.domain import LLMClient
from kalenjin.llm.gemini_client import GeminiLLMClient, validate_gemini_api_key
from kalenjin.security.encryption import DecryptionError, decrypt, encrypt


class GeminiNotConnectedError(Exception):
    """Raised by `client()` when the user has never set a Gemini API key."""


class GeminiReauthRequiredError(Exception):
    """Raised by `client()` when the stored key can't be decrypted — e.g. after an
    encryption-key rotation (ADR-0010). The remedy is the same as never having
    connected: the user must set a key again."""


class GeminiInvalidKeyError(Exception):
    """Raised by `set_key()` when Gemini rejects the submitted key."""


class GeminiConnection(Protocol):
    """This user's connection to Gemini (ADR-0007) — owns key validation, storage,
    decryption, and client construction, so callers never see ciphertext or an
    encryption key."""

    def set_key(self, api_key: str) -> None:
        """Validates `api_key` with a real Gemini call, then stores it encrypted
        (issue #29) — a typo is caught immediately rather than at the next rapport
        generation. Resubmitting replaces the previous key (rotation). Raises
        `GeminiInvalidKeyError` if Gemini rejects the key."""
        ...

    def client(self) -> LLMClient:
        """A ready-to-use `LLMClient` for this user. Raises `GeminiNotConnectedError`
        if no key was ever set, or `GeminiReauthRequiredError` if the stored key can't
        be decrypted."""
        ...


class UserGeminiConnection:
    """`GeminiConnection` backed by a real `UserRepository` and encryption key."""

    def __init__(self, user_id: int, user_repo: UserRepository, encryption_key: str) -> None:
        self._user_id = user_id
        self._user_repo = user_repo
        self._encryption_key = encryption_key

    def set_key(self, api_key: str) -> None:
        if not validate_gemini_api_key(api_key):
            raise GeminiInvalidKeyError("Invalid Gemini API key")
        encrypted = encrypt(api_key, self._encryption_key)
        self._user_repo.set_gemini_api_key(self._user_id, encrypted)

    def client(self) -> LLMClient:
        user = self._user_repo.find_by_id(self._user_id)
        if user is None or user.gemini_api_key_encrypted is None:
            raise GeminiNotConnectedError("Connect your Gemini API key first")
        try:
            api_key = decrypt(user.gemini_api_key_encrypted, self._encryption_key)
        except DecryptionError as exc:
            raise GeminiReauthRequiredError(
                "Your Gemini key could not be decrypted — connect it again"
            ) from exc
        return GeminiLLMClient(api_key=api_key)
