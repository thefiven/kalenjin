from google import genai
from google.genai import errors


class GeminiLLMClient:
    """Adapter over `google-genai` implementing `llm.domain.LLMClient`.

    Gemini is used by pragmatism (free tier, low call volume) — see ADR-0002.
    No Gemini-specific type leaves this module; callers only see `generate`.
    """

    def __init__(self, api_key: str, model: str = "gemini-flash-latest") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(model=self._model, contents=prompt)
        if response.text is None:
            raise RuntimeError("Gemini returned an empty response")
        return response.text


def validate_gemini_api_key(api_key: str) -> bool:
    """Confirms `api_key` actually authenticates against Gemini (issue #29) — a
    self-service onboarding submission gets a clear rejection immediately, rather
    than a working-looking submission that only fails at the next rapport
    generation."""
    try:
        GeminiLLMClient(api_key=api_key).generate("Reply with OK.")
    except errors.ClientError:
        return False
    return True
