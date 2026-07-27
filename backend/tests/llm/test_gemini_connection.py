from datetime import datetime
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from kalenjin.auth.domain import UserRecord
from kalenjin.llm.connection import (
    GeminiInvalidKeyError,
    GeminiNotConnectedError,
    GeminiReauthRequiredError,
    UserGeminiConnection,
)
from kalenjin.security.encryption import decrypt, encrypt
from support.fakes import FakeUserRepository

KEY = Fernet.generate_key().decode()


def _user(gemini_key: str | None = None) -> UserRecord:
    return UserRecord(
        id=1,
        google_subject="test-subject",
        email="friend@x.com",
        created_at=datetime.now(),
        gemini_api_key_encrypted=gemini_key,
    )


def test_client_raises_not_connected_when_no_key_was_ever_set() -> None:
    connection = UserGeminiConnection(1, FakeUserRepository(existing=[_user()]), KEY)

    with pytest.raises(GeminiNotConnectedError):
        connection.client()


@patch("kalenjin.llm.connection.validate_gemini_api_key", return_value=True)
def test_set_key_stores_it_encrypted_when_valid(mock_validate: object) -> None:
    user_repo = FakeUserRepository(existing=[_user()])
    connection = UserGeminiConnection(1, user_repo, KEY)

    connection.set_key("my-real-key")

    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.gemini_api_key_encrypted is not None
    assert stored.gemini_api_key_encrypted != "my-real-key"
    assert decrypt(stored.gemini_api_key_encrypted, KEY) == "my-real-key"


@patch("kalenjin.llm.connection.validate_gemini_api_key", return_value=False)
def test_set_key_rejects_an_invalid_key_and_stores_nothing(mock_validate: object) -> None:
    user_repo = FakeUserRepository(existing=[_user()])
    connection = UserGeminiConnection(1, user_repo, KEY)

    with pytest.raises(GeminiInvalidKeyError):
        connection.set_key("bad-key")

    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.gemini_api_key_encrypted is None


@patch("kalenjin.llm.connection.validate_gemini_api_key", return_value=True)
def test_resubmitting_a_key_replaces_the_previous_one(mock_validate: object) -> None:
    user_repo = FakeUserRepository(existing=[_user()])
    connection = UserGeminiConnection(1, user_repo, KEY)

    connection.set_key("first-key")
    connection.set_key("second-key")

    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert decrypt(stored.gemini_api_key_encrypted or "", KEY) == "second-key"


def test_client_builds_a_gemini_client_from_the_users_decrypted_key() -> None:
    user_repo = FakeUserRepository(existing=[_user(gemini_key=encrypt("real-key", KEY))])
    connection = UserGeminiConnection(1, user_repo, KEY)

    with patch("kalenjin.llm.connection.GeminiLLMClient") as gemini_cls:
        connection.client()

    gemini_cls.assert_called_once_with(api_key="real-key")


def test_client_raises_reauth_required_when_the_stored_key_cannot_be_decrypted() -> None:
    wrong_key = Fernet.generate_key().decode()
    user_repo = FakeUserRepository(existing=[_user(gemini_key=encrypt("real-key", wrong_key))])
    connection = UserGeminiConnection(1, user_repo, KEY)

    with pytest.raises(GeminiReauthRequiredError):
        connection.client()
