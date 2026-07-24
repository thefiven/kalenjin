import os

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from kalenjin.db.models import Base

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
