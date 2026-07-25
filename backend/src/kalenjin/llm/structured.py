from __future__ import annotations

import json
from typing import Any


class StructuredResponseError(Exception):
    """Raised when an LLM response can't be parsed as JSON, after stripping any
    markdown code fence.

    Field/shape validation (e.g. required keys, expected types) is intentionally not
    this module's concern — callers validate the parsed structure themselves and
    raise their own domain-specific error (e.g. `PlanGenerationError`,
    `RapportGenerationError`), typically re-wrapping this one.
    """


def _strip_code_fences(response: str) -> str:
    text = response.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        text = text.removesuffix("```").strip()
    return text


def parse_json_response(response: str) -> Any:
    """Strips a markdown code fence if present, then parses the result as JSON.

    Raises `StructuredResponseError`, chained from the underlying `JSONDecodeError`,
    if the result isn't valid JSON.
    """
    try:
        return json.loads(_strip_code_fences(response))
    except json.JSONDecodeError as exc:
        raise StructuredResponseError(f"LLM response was not valid JSON: {response!r}") from exc
