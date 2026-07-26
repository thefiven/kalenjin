from unittest.mock import MagicMock, patch

from google.genai import errors

from kalenjin.llm.gemini_client import validate_gemini_api_key


@patch("kalenjin.llm.gemini_client.genai")
def test_returns_true_when_gemini_accepts_the_key(genai_module: MagicMock) -> None:
    genai_module.Client.return_value.models.generate_content.return_value = MagicMock(text="OK")

    assert validate_gemini_api_key("a-real-key") is True


@patch("kalenjin.llm.gemini_client.genai")
def test_returns_false_when_gemini_rejects_the_key(genai_module: MagicMock) -> None:
    genai_module.Client.return_value.models.generate_content.side_effect = errors.ClientError(
        400, {"error": {"message": "API key not valid"}}
    )

    assert validate_gemini_api_key("a-bad-key") is False
