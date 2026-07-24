from typing import Protocol


class LLMClient(Protocol):
    """A generic text-in/text-out LLM boundary.

    Kept provider-agnostic (ADR-0002): no Gemini-specific types leak past this
    Protocol, so swapping providers later doesn't ripple through call sites.
    """

    def generate(self, prompt: str) -> str: ...
