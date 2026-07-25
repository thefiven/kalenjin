import pytest

from kalenjin.llm.structured import StructuredResponseError, parse_json_response


def test_parses_valid_json() -> None:
    result = parse_json_response('{"strengths": "Good pace.", "improvements": "Add strides."}')

    assert result == {"strengths": "Good pace.", "improvements": "Add strides."}


def test_parses_json_wrapped_in_a_markdown_code_fence() -> None:
    response = '```json\n{"day_offset": 0, "type": "easy"}\n```'

    result = parse_json_response(response)

    assert result == {"day_offset": 0, "type": "easy"}


def test_parses_a_json_array() -> None:
    result = parse_json_response('[{"day_offset": 0}, {"day_offset": 3}]')

    assert result == [{"day_offset": 0}, {"day_offset": 3}]


def test_raises_a_structured_response_error_on_malformed_json() -> None:
    with pytest.raises(StructuredResponseError) as exc_info:
        parse_json_response("not json at all")

    assert "not json at all" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_does_not_validate_missing_expected_fields() -> None:
    """Field/shape validation is the caller's responsibility, not this module's —
    valid JSON that's missing keys a caller might require still parses successfully."""
    result = parse_json_response('{"unrelated_key": "value"}')

    assert result == {"unrelated_key": "value"}
