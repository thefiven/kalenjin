from datetime import date
from unittest.mock import MagicMock, patch

from kalenjin.garmin.client import GarminActivityClient


@patch("kalenjin.garmin.client.Garmin")
def test_login_resumes_from_the_given_session(garmin_cls: MagicMock) -> None:
    client = GarminActivityClient(email="a@b.com", password="secret", session='{"di_token": "abc"}')

    client.login()

    garmin_cls.return_value.login.assert_called_once_with('{"di_token": "abc"}')


@patch("kalenjin.garmin.client.Garmin")
def test_login_with_no_session_does_a_plain_credential_login(garmin_cls: MagicMock) -> None:
    client = GarminActivityClient(email="a@b.com", password="secret")

    client.login()

    garmin_cls.return_value.login.assert_called_once_with(None)


@patch("kalenjin.garmin.client.Garmin")
def test_constructs_the_underlying_client_with_credentials_only(garmin_cls: MagicMock) -> None:
    GarminActivityClient(email="a@b.com", password="secret", session='{"di_token": "abc"}')

    garmin_cls.assert_called_once_with(email="a@b.com", password="secret")


@patch("kalenjin.garmin.client.Garmin")
def test_dump_session_delegates_to_the_underlying_clients_dumps(garmin_cls: MagicMock) -> None:
    garmin_cls.return_value.client.dumps.return_value = '{"di_token": "abc"}'
    client = GarminActivityClient(email="a@b.com", password="secret")

    assert client.dump_session() == '{"di_token": "abc"}'


@patch("kalenjin.garmin.client.Garmin")
def test_fetch_activities_delegates_to_get_activities_by_date_with_iso_dates(
    garmin_cls: MagicMock,
) -> None:
    garmin_cls.return_value.get_activities_by_date.return_value = [{"activityId": "1"}]
    client = GarminActivityClient(email="a@b.com", password="secret")

    activities = client.fetch_activities(date(2024, 1, 1), date(2024, 1, 31))

    garmin_cls.return_value.get_activities_by_date.assert_called_once_with(
        "2024-01-01", "2024-01-31"
    )
    assert activities == [{"activityId": "1"}]
