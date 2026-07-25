from __future__ import annotations

import logging
from datetime import date

from kalenjin.config.settings import DbConfig, GarminConfig
from kalenjin.db.repository import SqlAlchemyActivityRepository
from kalenjin.db.session import make_engine, make_session_factory, session_scope
from kalenjin.garmin.client import GarminActivityClient
from kalenjin.sync.service import sync_activities

logger = logging.getLogger(__name__)


def prompt_mfa_via_console() -> str:
    return input("Garmin MFA code: ")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    garmin_config = GarminConfig()  # type: ignore[call-arg]  # fields are sourced from the environment
    db_config = DbConfig()  # type: ignore[call-arg]  # fields are sourced from the environment

    source = GarminActivityClient(
        email=garmin_config.garmin_email,
        password=garmin_config.garmin_password,
        tokenstore=garmin_config.garmin_tokenstore,
        prompt_mfa=prompt_mfa_via_console,
    )
    source.login()

    engine = make_engine(db_config.database_url)
    session_factory = make_session_factory(engine)

    with session_scope(session_factory) as session:
        repo = SqlAlchemyActivityRepository(session)
        result = sync_activities(source, repo, today=date.today())

    logger.info("Synced %d new activities", result.imported_count)


if __name__ == "__main__":
    main()
