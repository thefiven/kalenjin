from datetime import date
from unittest.mock import MagicMock, patch

from kalenjin.garmin.client import GarminActivityClient


@patch("kalenjin.garmin.client.Garmin")
def test_login_delegates_to_the_underlying_client_with_the_tokenstore(
    garmin_cls: MagicMock,
) -> None:
    client = GarminActivityClient(email="a@b.com", password="secret", tokenstore="/tmp/tokens")

    client.login()

    garmin_cls.return_value.login.assert_called_once_with("/tmp/tokens")


@patch("kalenjin.garmin.client.Garmin")
def test_constructs_the_underlying_client_with_credentials_and_mfa_prompt(
    garmin_cls: MagicMock,
) -> None:
    def prompt_mfa() -> str:
        return "123456"

    GarminActivityClient(
        email="a@b.com", password="secret", tokenstore="/tmp/tokens", prompt_mfa=prompt_mfa
    )

    garmin_cls.assert_called_once_with(email="a@b.com", password="secret", prompt_mfa=prompt_mfa)


@patch("kalenjin.garmin.client.Garmin")
def test_dump_session_delegates_to_the_underlying_clients_dumps(garmin_cls: MagicMock) -> None:
    garmin_cls.return_value.client.dumps.return_value = '{"di_token": "abc"}'
    client = GarminActivityClient(email="a@b.com", password="secret", tokenstore="/tmp/tokens")

    assert client.dump_session() == '{"di_token": "abc"}'


@patch("kalenjin.garmin.client.Garmin")
def test_fetch_activities_delegates_to_get_activities_by_date_with_iso_dates(
    garmin_cls: MagicMock,
) -> None:
    garmin_cls.return_value.get_activities_by_date.return_value = [{"activityId": "1"}]
    client = GarminActivityClient(email="a@b.com", password="secret", tokenstore="/tmp/tokens")

    activities = client.fetch_activities(date(2024, 1, 1), date(2024, 1, 31))

    garmin_cls.return_value.get_activities_by_date.assert_called_once_with(
        "2024-01-01", "2024-01-31"
    )
    assert activities == [{"activityId": "1"}]
