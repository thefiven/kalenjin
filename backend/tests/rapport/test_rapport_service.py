from datetime import datetime

import pytest

from kalenjin.rapport.service import RapportGenerationError, generate_rapport, select_history
from kalenjin.sync.domain import ActivityRecord
from support.fakes import FakeLLMClient


def _activity(activity_id: str, started_at: datetime, distance: float = 5000.0) -> ActivityRecord:
    return ActivityRecord(
        garmin_activity_id=activity_id,
        sport="running",
        started_at=started_at,
        duration_seconds=1800.0,
        distance_meters=distance,
        average_heart_rate=150.0,
        raw_payload={},
    )


def test_generate_rapport_includes_activity_metrics_in_the_prompt() -> None:
    llm = FakeLLMClient('{"strengths": "Good pace.", "improvements": "Add strides."}')
    activity = _activity("1", datetime(2024, 6, 1, 7, 30))

    generate_rapport(activity, history=[], llm=llm)

    (prompt,) = llm.prompts
    assert "running" in prompt
    assert "5000.0" in prompt
    assert "1800.0" in prompt
    assert "150.0" in prompt


def test_generate_rapport_includes_recent_history_in_the_prompt() -> None:
    llm = FakeLLMClient('{"strengths": "Good pace.", "improvements": "Add strides."}')
    activity = _activity("2", datetime(2024, 6, 5, 7, 30), distance=6000.0)
    history = [_activity("1", datetime(2024, 6, 1, 7, 30), distance=5000.0)]

    generate_rapport(activity, history=history, llm=llm)

    (prompt,) = llm.prompts
    assert "5000.0" in prompt
    assert "6000.0" in prompt


def test_generate_rapport_parses_the_json_response_into_a_record() -> None:
    llm = FakeLLMClient('{"strengths": "Good pace.", "improvements": "Add strides."}')
    activity = _activity("1", datetime(2024, 6, 1, 7, 30))

    rapport = generate_rapport(activity, history=[], llm=llm, now=datetime(2024, 6, 1, 8, 0))

    assert rapport.garmin_activity_id == "1"
    assert rapport.strengths == "Good pace."
    assert rapport.improvements == "Add strides."
    assert rapport.generated_at == datetime(2024, 6, 1, 8, 0)


def test_generate_rapport_strips_markdown_code_fences_from_the_response() -> None:
    llm = FakeLLMClient('```json\n{"strengths": "Good pace.", "improvements": "Add strides."}\n```')
    activity = _activity("1", datetime(2024, 6, 1, 7, 30))

    rapport = generate_rapport(activity, history=[], llm=llm)

    assert rapport.strengths == "Good pace."
    assert rapport.improvements == "Add strides."


def test_generate_rapport_raises_on_malformed_response() -> None:
    llm = FakeLLMClient("not json")
    activity = _activity("1", datetime(2024, 6, 1, 7, 30))

    with pytest.raises(RapportGenerationError):
        generate_rapport(activity, history=[], llm=llm)


def test_generate_rapport_raises_when_expected_keys_are_missing() -> None:
    llm = FakeLLMClient('{"strengths": "Good pace."}')
    activity = _activity("1", datetime(2024, 6, 1, 7, 30))

    with pytest.raises(RapportGenerationError):
        generate_rapport(activity, history=[], llm=llm)


def test_generate_rapport_raises_when_response_values_are_not_strings() -> None:
    llm = FakeLLMClient('{"strengths": ["Good pace."], "improvements": "Add strides."}')
    activity = _activity("1", datetime(2024, 6, 1, 7, 30))

    with pytest.raises(RapportGenerationError):
        generate_rapport(activity, history=[], llm=llm)


def test_select_history_excludes_the_activity_itself() -> None:
    activity = _activity("2", datetime(2024, 6, 5, 7, 30))
    activities = [activity, _activity("1", datetime(2024, 6, 1, 7, 30))]

    history = select_history(activity, activities)

    assert [a.garmin_activity_id for a in history] == ["1"]


def test_select_history_caps_at_the_history_size() -> None:
    activity = _activity("0", datetime(2024, 6, 10, 7, 30))
    activities = [activity] + [_activity(str(i), datetime(2024, 6, i, 7, 30)) for i in range(1, 8)]

    history = select_history(activity, activities)

    assert len(history) == 5
