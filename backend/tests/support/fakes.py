from dataclasses import replace
from datetime import date, datetime
from typing import Any

from kalenjin.auth.domain import GoogleIdentity, UserRecord
from kalenjin.auth.google_client import GoogleAuthError
from kalenjin.garmin.connection import (
    Connected,
    GarminConnectOutcome,
    GarminNotConnectedError,
)
from kalenjin.garmin.domain import GarminSessionClient
from kalenjin.llm.connection import GeminiNotConnectedError
from kalenjin.llm.domain import LLMClient
from kalenjin.plan.domain import ObjectifRecord, PlanRecord, SeanceRecord
from kalenjin.rapport.domain import RapportRecord
from kalenjin.sync.domain import ActivityRecord, DateRange


class RejectsPush:
    """Mixin for `ActivitySource`-only test fakes that still need to satisfy
    `garmin.domain.GarminSessionClient`'s shape, since `FakeGarminConnection.session()`
    is typed to return one — raises if push is ever actually exercised through one of
    these fakes."""

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
    exercise `/sync`'s Garmin push can pass this alone as `FakeGarminConnection`'s
    `session=`.
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


class FakeGarminConnection:
    """In-memory `garmin.connection.GarminConnection` for HTTP-layer wiring tests —
    the MFA state machine, decryption, and session refresh are tested directly
    against the real implementation in tests/garmin/test_garmin_connection.py; this
    fake just returns canned outcomes so route handlers can be tested in isolation."""

    def __init__(
        self,
        session: GarminSessionClient | None = None,
        connect_result: GarminConnectOutcome | Exception = Connected(),
        complete_mfa_result: GarminConnectOutcome | Exception = Connected(),
    ) -> None:
        self._session = session
        self._connect_result = connect_result
        self._complete_mfa_result = complete_mfa_result
        self.disconnected = False

    def connect(self, email: str, password: str) -> GarminConnectOutcome:
        if isinstance(self._connect_result, Exception):
            raise self._connect_result
        return self._connect_result

    def complete_mfa(self, pending_login_id: str, mfa_code: str) -> GarminConnectOutcome:
        if isinstance(self._complete_mfa_result, Exception):
            raise self._complete_mfa_result
        return self._complete_mfa_result

    def session(self) -> GarminSessionClient:
        if self._session is None:
            raise GarminNotConnectedError("no Garmin session configured on this fake")
        return self._session

    def disconnect(self) -> None:
        self.disconnected = True


class FakeGeminiConnection:
    """In-memory `llm.connection.GeminiConnection` for HTTP-layer wiring tests — key
    validation/decryption is tested directly against the real implementation in
    tests/llm/test_gemini_connection.py."""

    def __init__(
        self, client: LLMClient | None = None, set_key_error: Exception | None = None
    ) -> None:
        self._client = client
        self._set_key_error = set_key_error
        self.set_keys: list[str] = []

    def set_key(self, api_key: str) -> None:
        self.set_keys.append(api_key)
        if self._set_key_error is not None:
            raise self._set_key_error

    def client(self) -> LLMClient:
        if self._client is None:
            raise GeminiNotConnectedError("no Gemini client configured on this fake")
        return self._client


class FakeGoogleIdentityVerifier:
    """In-memory `auth.domain.GoogleIdentityVerifier` — no real Google call."""

    def __init__(self, identity: GoogleIdentity | None = None) -> None:
        self._identity = identity
        self.exchanged_codes: list[str] = []

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        return f"https://accounts.google.com/fake-consent?state={state}"

    def exchange_code(self, code: str, redirect_uri: str) -> GoogleIdentity:
        self.exchanged_codes.append(code)
        if self._identity is None:
            raise GoogleAuthError("no identity configured for this fake")
        return self._identity


class FakeUserRepository:
    """In-memory `auth.domain.UserRepository` — no real database."""

    def __init__(
        self,
        allowed_emails: set[str] | None = None,
        existing: list[UserRecord] | None = None,
    ) -> None:
        self._allowed_emails = set(allowed_emails or set())
        self._users = list(existing or [])
        self._next_id = max((u.id or 0 for u in self._users), default=0) + 1

    def is_email_allowed(self, email: str) -> bool:
        return email in self._allowed_emails

    def add_to_allowlist(self, email: str) -> None:
        self._allowed_emails.add(email)

    def revoke_access(self, email: str) -> None:
        self._allowed_emails.discard(email)
        for i, u in enumerate(self._users):
            if u.email == email:
                self._users[i] = replace(u, is_active=False)

    def find_by_google_subject(self, subject: str) -> UserRecord | None:
        return next((u for u in self._users if u.google_subject == subject), None)

    def find_by_id(self, user_id: int) -> UserRecord | None:
        return next((u for u in self._users if u.id == user_id and u.is_active), None)

    def create(self, subject: str, email: str) -> UserRecord:
        user = UserRecord(
            id=self._next_id, google_subject=subject, email=email, created_at=datetime.now()
        )
        self._next_id += 1
        self._users.append(user)
        return user

    def set_gemini_api_key(self, user_id: int, encrypted_key: str) -> None:
        idx = next(i for i, u in enumerate(self._users) if u.id == user_id)
        self._users[idx] = replace(self._users[idx], gemini_api_key_encrypted=encrypted_key)

    def set_garmin_credentials(self, user_id: int, email: str, encrypted_password: str) -> None:
        idx = next(i for i, u in enumerate(self._users) if u.id == user_id)
        self._users[idx] = replace(
            self._users[idx], garmin_email=email, garmin_password_encrypted=encrypted_password
        )

    def set_garmin_session(self, user_id: int, encrypted_session: str) -> None:
        idx = next(i for i, u in enumerate(self._users) if u.id == user_id)
        self._users[idx] = replace(self._users[idx], garmin_session_encrypted=encrypted_session)

    def clear_garmin_credentials(self, user_id: int) -> None:
        idx = next(i for i, u in enumerate(self._users) if u.id == user_id)
        self._users[idx] = replace(
            self._users[idx],
            garmin_email=None,
            garmin_password_encrypted=None,
            garmin_session_encrypted=None,
        )


def raw_activity(activity_id: str, started_at: str = "2024-06-01 07:30:00") -> dict[str, Any]:
    return {
        "activityId": activity_id,
        "activityType": {"typeKey": "running"},
        "startTimeLocal": started_at,
        "duration": 1800.0,
        "distance": 5000.0,
        "averageHR": 150,
    }
