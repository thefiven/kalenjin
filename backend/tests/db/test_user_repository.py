import pytest
from sqlalchemy.orm import Session

from kalenjin.db.repository import SqlAlchemyUserRepository

pytestmark = pytest.mark.integration


def test_is_email_allowed_is_false_for_an_unknown_email(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)

    assert repo.is_email_allowed("friend@example.com") is False


def test_add_to_allowlist_then_email_is_allowed(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)

    repo.add_to_allowlist("friend@example.com")

    assert repo.is_email_allowed("friend@example.com") is True


def test_add_to_allowlist_is_idempotent(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)

    repo.add_to_allowlist("friend@example.com")
    repo.add_to_allowlist("friend@example.com")

    assert repo.is_email_allowed("friend@example.com") is True


def test_create_then_find_by_google_subject_returns_the_same_user(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)

    created = repo.create("google-subject-1", "friend@example.com")
    found = repo.find_by_google_subject("google-subject-1")

    assert found is not None
    assert found.id == created.id
    assert found.email == "friend@example.com"


def test_find_by_google_subject_returns_none_when_missing(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)

    assert repo.find_by_google_subject("no-such-subject") is None


def test_find_by_id_returns_the_matching_user(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    created = repo.create("google-subject-1", "friend@example.com")
    assert created.id is not None

    found = repo.find_by_id(created.id)

    assert found is not None
    assert found.google_subject == "google-subject-1"


def test_find_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)

    assert repo.find_by_id(999_999) is None


def test_new_user_has_no_gemini_api_key(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)

    created = repo.create("google-subject-1", "friend@example.com")

    assert created.gemini_api_key_encrypted is None


def test_set_gemini_api_key_then_find_by_id_returns_it(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    created = repo.create("google-subject-1", "friend@example.com")
    assert created.id is not None

    repo.set_gemini_api_key(created.id, "ciphertext-1")

    found = repo.find_by_id(created.id)
    assert found is not None
    assert found.gemini_api_key_encrypted == "ciphertext-1"


def test_set_gemini_api_key_replaces_an_existing_key_on_rotation(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    created = repo.create("google-subject-1", "friend@example.com")
    assert created.id is not None
    repo.set_gemini_api_key(created.id, "ciphertext-old")

    repo.set_gemini_api_key(created.id, "ciphertext-new")

    found = repo.find_by_id(created.id)
    assert found is not None
    assert found.gemini_api_key_encrypted == "ciphertext-new"
