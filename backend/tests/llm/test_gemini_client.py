from unittest.mock import MagicMock, patch

from kalenjin.llm.gemini_client import GeminiLLMClient


@patch("kalenjin.llm.gemini_client.genai")
def test_constructs_the_underlying_client_with_the_api_key(genai_module: MagicMock) -> None:
    GeminiLLMClient(api_key="secret")

    genai_module.Client.assert_called_once_with(api_key="secret")


@patch("kalenjin.llm.gemini_client.genai")
def test_generate_delegates_to_generate_content_with_the_configured_model(
    genai_module: MagicMock,
) -> None:
    genai_module.Client.return_value.models.generate_content.return_value = MagicMock(
        text="a coaching response"
    )
    client = GeminiLLMClient(api_key="secret", model="gemini-2.0-flash")

    result = client.generate("analyze this session")

    genai_module.Client.return_value.models.generate_content.assert_called_once_with(
        model="gemini-2.0-flash", contents="analyze this session"
    )
    assert result == "a coaching response"
