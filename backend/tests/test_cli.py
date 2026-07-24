from contextlib import contextmanager
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

from kalenjin import cli
from kalenjin.sync.service import SyncResult


@patch("kalenjin.cli.sync_activities")
@patch("kalenjin.cli.SqlAlchemyActivityRepository")
@patch("kalenjin.cli.session_scope")
@patch("kalenjin.cli.make_session_factory")
@patch("kalenjin.cli.make_engine")
@patch("kalenjin.cli.GarminActivityClient")
@patch("kalenjin.cli.Settings")
def test_main_wires_settings_into_garmin_client_and_syncs(
    settings_cls: MagicMock,
    garmin_client_cls: MagicMock,
    make_engine_mock: MagicMock,
    make_session_factory_mock: MagicMock,
    session_scope_mock: MagicMock,
    repository_cls: MagicMock,
    sync_activities_mock: MagicMock,
) -> None:
    settings_cls.return_value = MagicMock(
        garmin_email="a@b.com",
        garmin_password="secret",
        garmin_tokenstore="/tmp/tokens",
        database_url="postgresql://x",
    )
    fake_session = MagicMock()

    @contextmanager
    def fake_session_scope(_factory: Any) -> Any:
        yield fake_session

    session_scope_mock.side_effect = fake_session_scope
    sync_activities_mock.return_value = SyncResult(imported_count=3)

    cli.main()

    garmin_client_cls.assert_called_once_with(
        email="a@b.com",
        password="secret",
        tokenstore="/tmp/tokens",
        prompt_mfa=cli.prompt_mfa_via_console,
    )
    garmin_client_cls.return_value.login.assert_called_once()
    make_engine_mock.assert_called_once_with("postgresql://x")
    repository_cls.assert_called_once_with(fake_session)

    assert sync_activities_mock.call_args.args[0] is garmin_client_cls.return_value
    assert sync_activities_mock.call_args.args[1] is repository_cls.return_value
    assert sync_activities_mock.call_args.kwargs["today"] == date.today()
