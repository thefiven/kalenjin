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


def main(argv: list[str] | None = None) -> None:
    """Syncs Garmin activities for one user (issue #28 — `Activity` rows are per-user,
    so this CLI, which runs outside the web session/auth layer, needs to be told which
    `User` row to attribute the sync to)."""
    logging.basicConfig(level=logging.INFO)
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        raise SystemExit("Usage: kalenjin-sync <user-id>")
    try:
        user_id = int(args[0])
    except ValueError:
        raise SystemExit(f"<user-id> must be an integer, got {args[0]!r}") from None

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
        repo = SqlAlchemyActivityRepository(session, user_id)
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


def revoke_main(argv: list[str] | None = None) -> None:
    """Cuts off an invited person's access (issue #25 story 19) — the owner's one-off
    action, mirroring `invite_main`. Removes the email from the invite allowlist and
    deactivates any existing `User` row for it, so a session already issued to them
    stops working on its next authenticated request."""
    logging.basicConfig(level=logging.INFO)
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        raise SystemExit("Usage: kalenjin-revoke <email>")
    email = args[0]

    db_config = DbConfig()  # type: ignore[call-arg]  # fields are sourced from the environment
    engine = make_engine(db_config.database_url)
    session_factory = make_session_factory(engine)

    with session_scope(session_factory) as session:
        repo = SqlAlchemyUserRepository(session)
        repo.revoke_access(email)

    logger.info("Revoked %s — they can no longer sign in or use an existing session", email)


if __name__ == "__main__":
    main()
