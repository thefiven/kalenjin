from __future__ import annotations

import logging
from datetime import date

from kalenjin.config.settings import Settings
from kalenjin.db.repository import SqlAlchemyActivityRepository
from kalenjin.db.session import make_engine, make_session_factory, session_scope
from kalenjin.garmin.client import GarminActivityClient
from kalenjin.sync.service import sync_activities

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    settings = Settings()  # type: ignore[call-arg]  # fields are sourced from the environment

    source = GarminActivityClient(
        email=settings.garmin_email,
        password=settings.garmin_password,
        tokenstore=settings.garmin_tokenstore,
    )
    source.login()

    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)

    with session_scope(session_factory) as session:
        repo = SqlAlchemyActivityRepository(session)
        result = sync_activities(source, repo, today=date.today())

    logger.info("Synced %d new activities", result.imported_count)


if __name__ == "__main__":
    main()
