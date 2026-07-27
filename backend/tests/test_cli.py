from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kalenjin import cli
from kalenjin.garmin.connection import GarminNotConnectedError
from kalenjin.sync.service import SyncResult


@dataclass
class _CliMocks:
    garmin_connection_cls: MagicMock
    make_engine: MagicMock
    session_scope: MagicMock
    repository_cls: MagicMock
    sync_activities: MagicMock
    fake_session: MagicMock


@pytest.fixture
def cli_mocks() -> Iterator[_CliMocks]:
    with (
        patch("kalenjin.cli.sync_activities") as sync_activities,
        patch("kalenjin.cli.SqlAlchemyActivityRepository") as repository_cls,
        patch("kalenjin.cli.SqlAlchemyUserRepository"),
        patch("kalenjin.cli.session_scope") as session_scope,
        patch("kalenjin.cli.make_session_factory"),
        patch("kalenjin.cli.make_engine") as make_engine,
        patch("kalenjin.cli.UserGarminConnection") as garmin_connection_cls,
    ):
        fake_session = MagicMock()

        @contextmanager
        def fake_session_scope(_factory: Any) -> Any:
            yield fake_session

        session_scope.side_effect = fake_session_scope
        sync_activities.return_value = SyncResult(imported_count=0)

        yield _CliMocks(
            garmin_connection_cls=garmin_connection_cls,
            make_engine=make_engine,
            session_scope=session_scope,
            repository_cls=repository_cls,
            sync_activities=sync_activities,
            fake_session=fake_session,
        )


def test_main_builds_the_users_own_garmin_connection_and_syncs(
    cli_mocks: _CliMocks, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("SECRET_ENCRYPTION_KEY", "test-key")
    cli_mocks.sync_activities.return_value = SyncResult(imported_count=3)

    cli.main(["1"])

    cli_mocks.garmin_connection_cls.assert_called_once()
    assert cli_mocks.garmin_connection_cls.call_args.args[0] == 1
    assert cli_mocks.garmin_connection_cls.call_args.args[2] == "test-key"
    cli_mocks.garmin_connection_cls.return_value.session.assert_called_once_with()
    cli_mocks.make_engine.assert_called_once_with("postgresql://x")
    cli_mocks.repository_cls.assert_called_once_with(cli_mocks.fake_session, 1)

    call_args = cli_mocks.sync_activities.call_args
    assert call_args.args[0] is cli_mocks.garmin_connection_cls.return_value.session.return_value
    assert call_args.args[1] is cli_mocks.repository_cls.return_value
    assert call_args.kwargs["today"] == date.today()


def test_main_exits_clearly_when_the_user_needs_to_reconnect_garmin(
    cli_mocks: _CliMocks, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("SECRET_ENCRYPTION_KEY", "test-key")
    cli_mocks.garmin_connection_cls.return_value.session.side_effect = GarminNotConnectedError(
        "Connect your Garmin account first"
    )

    with pytest.raises(SystemExit):
        cli.main(["1"])

    cli_mocks.sync_activities.assert_not_called()


def test_main_requires_exactly_one_user_id_argument() -> None:
    with pytest.raises(SystemExit):
        cli.main([])

    with pytest.raises(SystemExit):
        cli.main(["1", "2"])


def test_main_requires_the_user_id_argument_to_be_an_integer() -> None:
    with pytest.raises(SystemExit):
        cli.main(["not-a-number"])


@dataclass
class _InviteCliMocks:
    make_engine: MagicMock
    repository_cls: MagicMock
    fake_session: MagicMock


@pytest.fixture
def invite_cli_mocks() -> Iterator[_InviteCliMocks]:
    with (
        patch("kalenjin.cli.SqlAlchemyUserRepository") as repository_cls,
        patch("kalenjin.cli.session_scope") as session_scope,
        patch("kalenjin.cli.make_session_factory"),
        patch("kalenjin.cli.make_engine") as make_engine,
    ):
        fake_session = MagicMock()

        @contextmanager
        def fake_session_scope(_factory: Any) -> Any:
            yield fake_session

        session_scope.side_effect = fake_session_scope

        yield _InviteCliMocks(
            make_engine=make_engine, repository_cls=repository_cls, fake_session=fake_session
        )


def test_invite_main_adds_the_email_to_the_allowlist(
    invite_cli_mocks: _InviteCliMocks, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")

    cli.invite_main(["friend@example.com"])

    invite_cli_mocks.make_engine.assert_called_once_with("postgresql://x")
    invite_cli_mocks.repository_cls.assert_called_once_with(invite_cli_mocks.fake_session)
    invite_cli_mocks.repository_cls.return_value.add_to_allowlist.assert_called_once_with(
        "friend@example.com"
    )


def test_invite_main_requires_exactly_one_email_argument() -> None:
    with pytest.raises(SystemExit):
        cli.invite_main([])

    with pytest.raises(SystemExit):
        cli.invite_main(["a@b.com", "extra-arg"])


def test_revoke_main_revokes_access_for_the_email(
    invite_cli_mocks: _InviteCliMocks, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")

    cli.revoke_main(["friend@example.com"])

    invite_cli_mocks.make_engine.assert_called_once_with("postgresql://x")
    invite_cli_mocks.repository_cls.assert_called_once_with(invite_cli_mocks.fake_session)
    invite_cli_mocks.repository_cls.return_value.revoke_access.assert_called_once_with(
        "friend@example.com"
    )


def test_revoke_main_requires_exactly_one_email_argument() -> None:
    with pytest.raises(SystemExit):
        cli.revoke_main([])

    with pytest.raises(SystemExit):
        cli.revoke_main(["a@b.com", "extra-arg"])
