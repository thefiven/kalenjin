from datetime import datetime

from kalenjin.sync.parser import parse_activity


def _raw_running_activity(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "activityId": 12345,
        "activityType": {"typeKey": "running"},
        "startTimeLocal": "2024-06-01 07:30:00",
        "duration": 1800.0,
        "distance": 5000.0,
        "averageHR": 155,
    }
    raw.update(overrides)
    return raw


def test_parses_core_fields() -> None:
    record = parse_activity(_raw_running_activity())

    assert record.garmin_activity_id == "12345"
    assert record.sport == "running"
    assert record.started_at == datetime(2024, 6, 1, 7, 30, 0)
    assert record.duration_seconds == 1800.0
    assert record.distance_meters == 5000.0
    assert record.average_heart_rate == 155


def test_keeps_the_raw_payload_verbatim() -> None:
    raw = _raw_running_activity()

    record = parse_activity(raw)

    assert record.raw_payload == raw


def test_missing_optional_fields_become_none() -> None:
    raw = _raw_running_activity()
    del raw["distance"]
    del raw["averageHR"]

    record = parse_activity(raw)

    assert record.distance_meters is None
    assert record.average_heart_rate is None


def test_unrecognized_sport_key_is_kept_as_is() -> None:
    record = parse_activity(_raw_running_activity(activityType={"typeKey": "trail_running"}))

    assert record.sport == "trail_running"
