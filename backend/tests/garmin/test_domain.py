from unittest.mock import MagicMock, patch

from kalenjin.garmin.client import GarminActivityClient
from kalenjin.garmin.domain import GarminSessionClient
from support.fakes import FakeSource


@patch("kalenjin.garmin.client.Garmin")
def test_garmin_activity_client_satisfies_garmin_session_client(garmin_cls: MagicMock) -> None:
    client = GarminActivityClient(email="a@b.com", password="secret")

    assert isinstance(client, GarminSessionClient)


def test_a_narrow_activity_only_fake_does_not_satisfy_garmin_session_client() -> None:
    assert not isinstance(FakeSource({}), GarminSessionClient)
