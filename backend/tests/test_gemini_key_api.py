from datetime import datetime
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient

from kalenjin.api import (
    app,
    get_activity_repository,
    get_current_user,
    get_encryption_config,
    get_llm_client,
    get_objectif_repository,
    get_plan_repository,
    get_user_repository,
)
from kalenjin.auth.domain import UserRecord
from kalenjin.config.settings import EncryptionConfig
from kalenjin.security.encryption import decrypt, encrypt
from support.api_client import overriding_dependencies
from support.fakes import (
    FakeObjectifRepository,
    FakePlanRepository,
    FakeRepository,
    FakeUserRepository,
)

TEST_ENCRYPTION_CONFIG = EncryptionConfig(secret_encryption_key=Fernet.generate_key().decode())


def _fake_user(user_id: int = 1, gemini_key: str | None = None) -> UserRecord:
    return UserRecord(
        id=user_id,
        google_subject="test-subject",
        email="friend@x.com",
        created_at=datetime.now(),
        gemini_api_key_encrypted=gemini_key,
    )


@patch("kalenjin.api.validate_gemini_api_key", return_value=True)
def test_set_gemini_api_key_stores_it_encrypted_when_valid(mock_validate: object) -> None:
    user_repo = FakeUserRepository(existing=[_fake_user()])

    with overriding_dependencies(
        {
            get_current_user: lambda: _fake_user(),
            get_user_repository: lambda: user_repo,
            get_encryption_config: lambda: TEST_ENCRYPTION_CONFIG,
        }
    ):
        response = TestClient(app).post("/users/me/gemini-key", json={"api_key": "my-real-key"})

    assert response.status_code == 204
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.gemini_api_key_encrypted is not None
    assert stored.gemini_api_key_encrypted != "my-real-key"
    assert (
        decrypt(stored.gemini_api_key_encrypted, TEST_ENCRYPTION_CONFIG.secret_encryption_key)
        == "my-real-key"
    )


@patch("kalenjin.api.validate_gemini_api_key", return_value=False)
def test_set_gemini_api_key_rejects_an_invalid_key_and_stores_nothing(
    mock_validate: object,
) -> None:
    user_repo = FakeUserRepository(existing=[_fake_user()])

    with overriding_dependencies(
        {
            get_current_user: lambda: _fake_user(),
            get_user_repository: lambda: user_repo,
            get_encryption_config: lambda: TEST_ENCRYPTION_CONFIG,
        }
    ):
        response = TestClient(app).post("/users/me/gemini-key", json={"api_key": "bad-key"})

    assert response.status_code == 400
    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.gemini_api_key_encrypted is None


@patch("kalenjin.api.validate_gemini_api_key", return_value=True)
def test_resubmitting_a_key_replaces_the_previous_one(mock_validate: object) -> None:
    user_repo = FakeUserRepository(existing=[_fake_user()])

    with overriding_dependencies(
        {
            get_current_user: lambda: _fake_user(),
            get_user_repository: lambda: user_repo,
            get_encryption_config: lambda: TEST_ENCRYPTION_CONFIG,
        }
    ):
        client = TestClient(app)
        client.post("/users/me/gemini-key", json={"api_key": "first-key"})
        client.post("/users/me/gemini-key", json={"api_key": "second-key"})

    stored = user_repo.find_by_id(1)
    assert stored is not None
    assert stored.gemini_api_key_encrypted is not None
    assert (
        decrypt(stored.gemini_api_key_encrypted, TEST_ENCRYPTION_CONFIG.secret_encryption_key)
        == "second-key"
    )


def test_get_llm_client_builds_gemini_client_from_the_users_decrypted_key() -> None:
    encrypted = encrypt("real-key", TEST_ENCRYPTION_CONFIG.secret_encryption_key)
    user = _fake_user(gemini_key=encrypted)

    with patch("kalenjin.api.GeminiLLMClient") as gemini_cls:
        get_llm_client(user=user, encryption_config=TEST_ENCRYPTION_CONFIG)

    gemini_cls.assert_called_once_with(api_key="real-key")


def test_get_llm_client_rejects_a_user_without_a_connected_key() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_llm_client(user=_fake_user(gemini_key=None), encryption_config=TEST_ENCRYPTION_CONFIG)

    assert exc_info.value.status_code == 400


def test_create_objectif_returns_a_clear_error_when_gemini_is_not_connected() -> None:
    with overriding_dependencies(
        {
            get_current_user: lambda: _fake_user(gemini_key=None),
            get_encryption_config: lambda: TEST_ENCRYPTION_CONFIG,
            get_activity_repository: lambda: FakeRepository(),
            get_objectif_repository: lambda: FakeObjectifRepository(),
            get_plan_repository: lambda: FakePlanRepository(),
        }
    ):
        response = TestClient(app).post(
            "/objectif",
            json={
                "sport": "running",
                "target_distance_meters": 10_000,
                "target_date": "2026-12-01",
            },
        )

    assert response.status_code == 400
