import os
from datetime import datetime

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from kalenjin.db.models import Base, User

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://kalenjin:kalenjin@localhost:5432/kalenjin",
)


@pytest.fixture(scope="session")
def engine() -> Engine:
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine: Engine) -> Session:
    """A session bound to a transaction that's rolled back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def user_id(db_session: Session) -> int:
    """A real `User` row (issue #28's per-user repositories have a `user_id` foreign
    key, so a real row must exist for the tests' inserts not to violate it)."""
    user = User(google_subject="test-subject", email="test@example.com", created_at=datetime.now())
    db_session.add(user)
    db_session.flush()
    assert user.id is not None
    return user.id


@pytest.fixture
def other_user_id(db_session: Session) -> int:
    """A second, distinct `User` row — for tests proving data isolation between
    users (issue #28)."""
    user = User(
        google_subject="other-test-subject", email="other@example.com", created_at=datetime.now()
    )
    db_session.add(user)
    db_session.flush()
    assert user.id is not None
    return user.id
