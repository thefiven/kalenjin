from dataclasses import replace
from datetime import date, datetime
from typing import Any

from kalenjin.plan.domain import ObjectifRecord, PlanRecord, SeanceRecord
from kalenjin.rapport.domain import RapportRecord
from kalenjin.sync.domain import ActivityRecord, DateRange


class RejectsPush:
    """Mixin for `ActivitySource`-only test fakes that still need to satisfy
    `garmin.domain.GarminSessionClient`'s shape, since `get_garmin_push_client` asserts
    on it — raises if push is ever actually exercised through one of these fakes."""

    def push_workout(self, seance: SeanceRecord, sport: str) -> str:
        raise NotImplementedError("push must not be exercised in tests using this fake")

    def delete_workout(self, workout_id: str) -> None:
        raise NotImplementedError("push must not be exercised in tests using this fake")


class FakeSource:
    """In-memory `sync.domain.ActivitySource` — no real Garmin call."""

    def __init__(self, activities_by_range: dict[tuple[date, date], list[dict[str, Any]]]) -> None:
        self._activities_by_range = activities_by_range
        self.calls: list[tuple[date, date]] = []

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        self.calls.append((start_date, end_date))
        return self._activities_by_range.get((start_date, end_date), [])


class FakeRepository:
    """In-memory `sync.domain.ActivityRepository` — no real database."""

    def __init__(self, existing: list[ActivityRecord] | None = None) -> None:
        self._existing = {a.garmin_activity_id: a for a in (existing or [])}
        self.upsert_calls: list[list[ActivityRecord]] = []

    def has_any(self) -> bool:
        return bool(self._existing)

    def latest_started_at(self) -> datetime | None:
        if not self._existing:
            return None
        return max(a.started_at for a in self._existing.values())

    def upsert_many(self, activities: list[ActivityRecord]) -> int:
        self.upsert_calls.append(activities)
        inserted = 0
        for activity in activities:
            if activity.garmin_activity_id not in self._existing:
                inserted += 1
            self._existing[activity.garmin_activity_id] = activity
        return inserted

    def list_activities(self, date_range: DateRange = DateRange()) -> list[ActivityRecord]:
        activities = self._existing.values()
        if date_range.since is not None:
            activities = (a for a in activities if a.started_at.date() >= date_range.since)
        if date_range.until is not None:
            activities = (a for a in activities if a.started_at.date() <= date_range.until)
        return sorted(activities, key=lambda a: a.started_at, reverse=True)

    def get_activity(self, garmin_activity_id: str) -> ActivityRecord | None:
        return self._existing.get(garmin_activity_id)


class FakeRapportRepository:
    """In-memory `rapport.domain.RapportRepository` — no real database."""

    def __init__(self, existing: list[RapportRecord] | None = None) -> None:
        self._existing = {r.garmin_activity_id: r for r in (existing or [])}

    def save(self, rapport: RapportRecord) -> None:
        self._existing[rapport.garmin_activity_id] = rapport

    def get_for_activity(self, garmin_activity_id: str) -> RapportRecord | None:
        return self._existing.get(garmin_activity_id)

    def list_recent(self, limit: int) -> list[RapportRecord]:
        return sorted(self._existing.values(), key=lambda r: r.generated_at, reverse=True)[:limit]


class FakeLLMClient:
    """In-memory `llm.domain.LLMClient` — no real Gemini call."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._response


class FakeObjectifRepository:
    """In-memory `plan.domain.ObjectifRepository` — no real database."""

    def __init__(self, existing: list[ObjectifRecord] | None = None) -> None:
        self._objectifs = list(existing or [])
        self._next_id = max((o.id or 0 for o in self._objectifs), default=0) + 1

    def save(self, objectif: ObjectifRecord) -> ObjectifRecord:
        saved = replace(objectif, id=self._next_id)
        self._next_id += 1
        self._objectifs.append(saved)
        return saved

    def get_active(self) -> ObjectifRecord | None:
        if not self._objectifs:
            return None
        return max(self._objectifs, key=lambda o: o.created_at)


class FakePlanRepository:
    """In-memory `plan.domain.PlanRepository` — no real database.

    Mutations apply immediately (unlike the real, session-backed repository, which only
    stages writes until something commits) — `commit_snapshots` instead records a copy
    of plan state each time `commit()` is called, so a test can verify a caller commits
    at the right points (see `plan.push.sync_plan_to_garmin`, which must commit after
    each successful Garmin push) without this fake having to simulate transaction
    rollback itself.
    """

    def __init__(self, existing: PlanRecord | None = None) -> None:
        self._plan = existing
        self._next_id = 1
        self.commit_snapshots: list[PlanRecord] = []
        if existing is not None:
            self._next_id = max((s.id or 0 for s in existing.seances), default=0) + 1

    def commit(self) -> None:
        if self._plan is not None:
            self.commit_snapshots.append(self._plan)

    def save(self, plan: PlanRecord) -> PlanRecord:
        seances = []
        for seance in plan.seances:
            seances.append(replace(seance, id=self._next_id, plan_id=1))
            self._next_id += 1
        self._plan = replace(plan, id=1, seances=seances)
        return self._plan

    def get_active(self) -> PlanRecord | None:
        return self._plan

    def update_seances(self, seances: list[SeanceRecord]) -> None:
        if self._plan is None:
            return
        by_id = {s.id: s for s in seances}
        self._plan = replace(
            self._plan,
            seances=[by_id.get(s.id, s) for s in self._plan.seances],
        )

    def replace_seances(
        self, removed_seance_ids: list[int], new_seances: list[SeanceRecord]
    ) -> list[SeanceRecord]:
        if self._plan is None:
            return []
        remaining = [s for s in self._plan.seances if s.id not in removed_seance_ids]
        inserted = []
        for seance in new_seances:
            inserted.append(replace(seance, id=self._next_id))
            self._next_id += 1
        self._plan = replace(self._plan, seances=remaining + inserted)
        return inserted


class FakeGarminPushClient:
    """In-memory `plan.domain.GarminPushClient` — no real Garmin Connect call.

    Also implements `sync.domain.ActivitySource` (returning no activities), since the
    real `GarminActivityClient` plays both roles behind a single login — tests that
    exercise `/sync`'s Garmin push can override `get_activity_source` with this alone.
    """

    def __init__(self, fail_at_push_number: int | None = None) -> None:
        """`fail_at_push_number`, if set, makes the Nth call to `push_workout` (1-indexed,
        counting only calls that reach this fake — i.e. past any earlier failure) raise
        instead of succeeding, to simulate a mid-batch Garmin failure."""
        self.pushed: list[tuple[SeanceRecord, str]] = []
        self.deleted: list[str] = []
        self._next_id = 1
        self._fail_at_push_number = fail_at_push_number
        self._push_attempts = 0

    def push_workout(self, seance: SeanceRecord, sport: str) -> str:
        self._push_attempts += 1
        if self._push_attempts == self._fail_at_push_number:
            raise RuntimeError("simulated Garmin push failure")
        self.pushed.append((seance, sport))
        workout_id = f"workout-{self._next_id}"
        self._next_id += 1
        return workout_id

    def delete_workout(self, workout_id: str) -> None:
        self.deleted.append(workout_id)

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        return []


def raw_activity(activity_id: str, started_at: str = "2024-06-01 07:30:00") -> dict[str, Any]:
    return {
        "activityId": activity_id,
        "activityType": {"typeKey": "running"},
        "startTimeLocal": started_at,
        "duration": 1800.0,
        "distance": 5000.0,
        "averageHR": 150,
    }
