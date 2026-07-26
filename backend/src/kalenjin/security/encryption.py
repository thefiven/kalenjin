from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class DecryptionError(Exception):
    """Raised when ciphertext can't be decrypted with the given key — a wrong key, or
    tampered/corrupted ciphertext. Wraps `cryptography`'s own exception so no
    Fernet-specific type leaves this module (ADR-0010)."""


def encrypt(plaintext: str, key: str) -> str:
    return Fernet(key.encode()).encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str, key: str) -> str:
    try:
        return Fernet(key.encode()).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise DecryptionError("Could not decrypt: wrong key or corrupted ciphertext") from exc
