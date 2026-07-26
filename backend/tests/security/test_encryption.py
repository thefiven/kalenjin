import pytest
from cryptography.fernet import Fernet

from kalenjin.security.encryption import DecryptionError, decrypt, encrypt

KEY = Fernet.generate_key().decode()
OTHER_KEY = Fernet.generate_key().decode()


def test_decrypt_reverses_encrypt() -> None:
    ciphertext = encrypt("hunter2", KEY)

    assert decrypt(ciphertext, KEY) == "hunter2"


def test_ciphertext_does_not_contain_the_plaintext() -> None:
    ciphertext = encrypt("hunter2", KEY)

    assert "hunter2" not in ciphertext


def test_decrypting_with_the_wrong_key_fails_loudly() -> None:
    ciphertext = encrypt("hunter2", KEY)

    with pytest.raises(DecryptionError):
        decrypt(ciphertext, OTHER_KEY)


def test_decrypting_corrupted_ciphertext_fails_loudly() -> None:
    with pytest.raises(DecryptionError):
        decrypt("not-a-valid-token", KEY)
