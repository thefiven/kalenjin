from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from kalenjin.garmin.client import GarminActivityClient
from kalenjin.plan.domain import SeanceRecord


def _seance(scheduled_date: date | None = date(2026, 1, 14)) -> SeanceRecord:
    return SeanceRecord(
        id=1,
        plan_id=1,
        week_start=date(2026, 1, 12),
        phase="base",
        detail="detailed",
        scheduled_date=scheduled_date,
        seance_type="easy",
        distance_meters=5000.0,
        theme=None,
        week_volume_meters=20_000,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


@patch("kalenjin.garmin.client.Garmin")
def test_push_workout_uploads_and_schedules_a_running_workout(garmin_cls: MagicMock) -> None:
    garmin_cls.return_value.upload_running_workout.return_value = {"workoutId": 42}
    client = GarminActivityClient(email="a@b.com", password="secret", tokenstore="/tmp/tokens")

    workout_id = client.push_workout(_seance(), sport="running")

    assert workout_id == "42"
    garmin_cls.return_value.upload_running_workout.assert_called_once()
    garmin_cls.return_value.schedule_workout.assert_called_once_with("42", "2026-01-14")


@patch("kalenjin.garmin.client.Garmin")
def test_push_workout_uploads_a_cycling_workout(garmin_cls: MagicMock) -> None:
    garmin_cls.return_value.upload_cycling_workout.return_value = {"workoutId": 7}
    client = GarminActivityClient(email="a@b.com", password="secret", tokenstore="/tmp/tokens")

    workout_id = client.push_workout(_seance(), sport="cycling")

    assert workout_id == "7"
    garmin_cls.return_value.upload_cycling_workout.assert_called_once()
    garmin_cls.return_value.schedule_workout.assert_called_once_with("7", "2026-01-14")


@patch("kalenjin.garmin.client.Garmin")
def test_push_workout_raises_when_the_seance_has_no_scheduled_date(
    garmin_cls: MagicMock,
) -> None:
    client = GarminActivityClient(email="a@b.com", password="secret", tokenstore="/tmp/tokens")

    with pytest.raises(ValueError, match="scheduled_date"):
        client.push_workout(_seance(scheduled_date=None), sport="running")


@patch("kalenjin.garmin.client.Garmin")
def test_delete_workout_delegates_to_the_underlying_client(garmin_cls: MagicMock) -> None:
    client = GarminActivityClient(email="a@b.com", password="secret", tokenstore="/tmp/tokens")

    client.delete_workout("42")

    garmin_cls.return_value.delete_workout.assert_called_once_with("42")
