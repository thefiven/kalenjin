from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kalenjin import cli
from kalenjin.sync.service import SyncResult


@dataclass
class _CliMocks:
    garmin_client_cls: MagicMock
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
        patch("kalenjin.cli.session_scope") as session_scope,
        patch("kalenjin.cli.make_session_factory"),
        patch("kalenjin.cli.make_engine") as make_engine,
        patch("kalenjin.cli.GarminActivityClient") as garmin_client_cls,
    ):
        fake_session = MagicMock()

        @contextmanager
        def fake_session_scope(_factory: Any) -> Any:
            yield fake_session

        session_scope.side_effect = fake_session_scope
        sync_activities.return_value = SyncResult(imported_count=0)

        yield _CliMocks(
            garmin_client_cls=garmin_client_cls,
            make_engine=make_engine,
            session_scope=session_scope,
            repository_cls=repository_cls,
            sync_activities=sync_activities,
            fake_session=fake_session,
        )


def test_main_wires_settings_into_garmin_client_and_syncs(
    cli_mocks: _CliMocks, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No GEMINI_API_KEY set — a plain activity sync must not require an LLM
    # credential, since main() only constructs GarminConfig and DbConfig.
    monkeypatch.setenv("GARMIN_EMAIL", "a@b.com")
    monkeypatch.setenv("GARMIN_PASSWORD", "secret")
    monkeypatch.setenv("GARMIN_TOKENSTORE", "/tmp/tokens")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    cli_mocks.sync_activities.return_value = SyncResult(imported_count=3)

    cli.main()

    cli_mocks.garmin_client_cls.assert_called_once_with(
        email="a@b.com",
        password="secret",
        tokenstore="/tmp/tokens",
        prompt_mfa=cli.prompt_mfa_via_console,
    )
    cli_mocks.garmin_client_cls.return_value.login.assert_called_once()
    cli_mocks.make_engine.assert_called_once_with("postgresql://x")
    cli_mocks.repository_cls.assert_called_once_with(cli_mocks.fake_session)

    call_args = cli_mocks.sync_activities.call_args
    assert call_args.args[0] is cli_mocks.garmin_client_cls.return_value
    assert call_args.args[1] is cli_mocks.repository_cls.return_value
    assert call_args.kwargs["today"] == date.today()


def test_main_does_not_require_a_gemini_api_key(
    cli_mocks: _CliMocks, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GARMIN_EMAIL", "a@b.com")
    monkeypatch.setenv("GARMIN_PASSWORD", "secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")

    cli.main()  # must not raise even though GEMINI_API_KEY is absent


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
