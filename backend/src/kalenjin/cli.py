from __future__ import annotations

import logging
import sys
from datetime import date

from kalenjin.config.settings import DbConfig, GarminConfig
from kalenjin.db.repository import SqlAlchemyActivityRepository, SqlAlchemyUserRepository
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


def invite_main(argv: list[str] | None = None) -> None:
    """Adds an email to the invite allowlist (ADR-0006, ADR-0008) — the owner's
    one-off action to let a new person sign in with Google, no self-service invite
    flow exists."""
    logging.basicConfig(level=logging.INFO)
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        raise SystemExit("Usage: kalenjin-invite <email>")
    email = args[0]

    db_config = DbConfig()  # type: ignore[call-arg]  # fields are sourced from the environment
    engine = make_engine(db_config.database_url)
    session_factory = make_session_factory(engine)

    with session_scope(session_factory) as session:
        repo = SqlAlchemyUserRepository(session)
        repo.add_to_allowlist(email)

    logger.info("Invited %s — they can now sign in with Google", email)


if __name__ == "__main__":
    main()
