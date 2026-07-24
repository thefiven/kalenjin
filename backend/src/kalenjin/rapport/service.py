from __future__ import annotations

import json
from datetime import datetime

from kalenjin.llm.domain import LLMClient
from kalenjin.rapport.domain import PERCEIVED_EFFORTS, RAPPORT_FLAGS, RapportRecord
from kalenjin.sync.domain import ActivityRecord

_REQUIRED_STRING_KEYS = ("strengths", "improvements")
HISTORY_SIZE = 5


class RapportGenerationError(Exception):
    """Raised when the LLM's response can't be parsed into a rapport."""


def select_history(
    activity: ActivityRecord, activities: list[ActivityRecord]
) -> list[ActivityRecord]:
    """The most recent activities before `activity`, for comparison context.

    `activities` is expected most-recent-first (as `ActivityRepository.list_activities` returns).
    """
    return [a for a in activities if a.garmin_activity_id != activity.garmin_activity_id][
        :HISTORY_SIZE
    ]


def _build_prompt(activity: ActivityRecord, history: list[ActivityRecord]) -> str:
    history_lines = "\n".join(
        f"- {past.started_at.date()}: {past.sport}, {past.distance_meters}m, "
        f"{past.duration_seconds}s, avg HR {past.average_heart_rate}"
        for past in history
    )
    return (
        "You are a running coach analyzing a completed training session. "
        "Respond with a single JSON object with exactly five keys: "
        '"strengths" and "improvements" (each a short paragraph of feedback); '
        '"completed_as_planned" (boolean); '
        f'"perceived_effort" (one of {list(PERCEIVED_EFFORTS)}); '
        f'"flag" (one of {list(RAPPORT_FLAGS)}, "none" unless the session notes or metrics '
        "suggest pain, illness, or that the session was missed/cut short). "
        "Do not include anything other than the JSON object.\n\n"
        f"Session: {activity.sport}, {activity.distance_meters}m, "
        f"{activity.duration_seconds}s, avg HR {activity.average_heart_rate}\n\n"
        f"Recent history:\n{history_lines or '(none)'}"
    )


def _strip_code_fences(response: str) -> str:
    text = response.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        text = text.removesuffix("```").strip()
    return text


def generate_rapport(
    activity: ActivityRecord,
    history: list[ActivityRecord],
    llm: LLMClient,
    now: datetime | None = None,
) -> RapportRecord:
    prompt = _build_prompt(activity, history)
    response = llm.generate(prompt)

    try:
        payload = json.loads(_strip_code_fences(response))
    except json.JSONDecodeError as exc:
        raise RapportGenerationError(f"LLM response was not valid JSON: {response!r}") from exc

    if not isinstance(payload, dict) or not all(
        isinstance(payload.get(key), str) for key in _REQUIRED_STRING_KEYS
    ):
        raise RapportGenerationError(f"LLM response is missing required string keys: {response!r}")

    if not isinstance(payload.get("completed_as_planned"), bool):
        raise RapportGenerationError(
            f"LLM response's completed_as_planned isn't boolean: {response!r}"
        )

    perceived_effort = payload.get("perceived_effort")
    if perceived_effort not in PERCEIVED_EFFORTS:
        raise RapportGenerationError(f"LLM response has an unknown perceived_effort: {response!r}")

    flag = payload.get("flag")
    if flag not in RAPPORT_FLAGS:
        raise RapportGenerationError(f"LLM response has an unknown flag: {response!r}")

    return RapportRecord(
        garmin_activity_id=activity.garmin_activity_id,
        strengths=payload["strengths"],
        improvements=payload["improvements"],
        generated_at=now if now is not None else datetime.now(),
        completed_as_planned=payload["completed_as_planned"],
        perceived_effort=perceived_effort,
        flag=flag,
    )
