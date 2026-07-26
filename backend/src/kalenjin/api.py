from __future__ import annotations

import secrets
from collections.abc import Iterator
from dataclasses import replace
from datetime import date, datetime
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from garminconnect.exceptions import GarminConnectAuthenticationError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kalenjin.auth.domain import GoogleIdentityVerifier, UserRecord, UserRepository
from kalenjin.auth.google_client import GoogleAuthError, GoogleOAuthClient
from kalenjin.auth.session import DEFAULT_SESSION_MAX_AGE_SECONDS, SessionCodec
from kalenjin.config.settings import AuthConfig, DbConfig, EncryptionConfig
from kalenjin.db.repository import (
    SqlAlchemyActivityRepository,
    SqlAlchemyObjectifRepository,
    SqlAlchemyPlanRepository,
    SqlAlchemyRapportRepository,
    SqlAlchemyUserRepository,
)
from kalenjin.db.session import make_engine, make_session_factory, session_scope
from kalenjin.garmin.client import GarminActivityClient
from kalenjin.garmin.domain import GarminSessionClient
from kalenjin.garmin.login import (
    GarminAuthError,
    GarminLoginSuccess,
    GarminMfaRequired,
    PendingGarminLoginStore,
    complete_garmin_mfa,
    initiate_garmin_login,
)
from kalenjin.llm.domain import LLMClient
from kalenjin.llm.gemini_client import GeminiLLMClient, validate_gemini_api_key
from kalenjin.plan.domain import (
    GarminPushClient,
    ObjectifRecord,
    ObjectifRepository,
    PlanRecord,
    PlanRepository,
    SeanceRecord,
)
from kalenjin.plan.generation import estimate_current_weekly_volume, generate_plan_seances
from kalenjin.rapport.domain import RapportRecord, RapportRepository
from kalenjin.rapport.orchestrator import RapportOrchestrator
from kalenjin.security.encryption import decrypt, encrypt
from kalenjin.sync.domain import ActivityRecord, ActivityRepository, ActivitySource, DateRange
from kalenjin.sync.orchestrator import SyncOrchestrator

RECENT_RAPPORTS_FOR_ADJUSTMENT = 5

SESSION_COOKIE_NAME = "kalenjin_session"
OAUTH_STATE_COOKIE_NAME = "kalenjin_oauth_state"
SESSION_MAX_AGE_SECONDS = DEFAULT_SESSION_MAX_AGE_SECONDS
OAUTH_STATE_MAX_AGE_SECONDS = 600

app = FastAPI(title="Kalenjin")


@lru_cache
def get_db_config() -> DbConfig:
    return DbConfig()  # type: ignore[call-arg]  # fields are sourced from the environment


@lru_cache
def get_auth_config() -> AuthConfig:
    return AuthConfig()  # type: ignore[call-arg]  # fields are sourced from the environment


@lru_cache
def get_encryption_config() -> EncryptionConfig:
    return EncryptionConfig()  # type: ignore[call-arg]  # fields are sourced from the environment


@lru_cache
def get_pending_garmin_login_store() -> PendingGarminLoginStore:
    return PendingGarminLoginStore()


def _get_db_session(db_config: DbConfig = Depends(get_db_config)) -> Iterator[Session]:
    """The request's shared unit-of-work seam: every `get_x_repository` provider below
    depends on this same callable, and FastAPI caches a dependency's result for the
    scope of one request — so any two repositories requested in the same endpoint
    share this one session, and can safely cross-reference rows written moments
    earlier in the same not-yet-committed transaction (e.g. `create_objectif` saving a
    Plan that references the Objectif it just saved)."""
    engine = make_engine(db_config.database_url)
    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        yield session


def get_user_repository(session: Session = Depends(_get_db_session)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_google_identity_verifier(
    auth_config: AuthConfig = Depends(get_auth_config),
) -> GoogleIdentityVerifier:
    return GoogleOAuthClient(
        client_id=auth_config.google_client_id, client_secret=auth_config.google_client_secret
    )


def get_session_codec(auth_config: AuthConfig = Depends(get_auth_config)) -> SessionCodec:
    return SessionCodec(
        secret_key=auth_config.session_secret_key, max_age_seconds=SESSION_MAX_AGE_SECONDS
    )


def get_current_user(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
    session_codec: SessionCodec = Depends(get_session_codec),
) -> UserRecord:
    """Every non-public endpoint depends on this (ADR-0008), superseding ADR-0005's
    VPN-only stance now that the app is multi-tenant. Activities, objectifs, plans,
    and rapports are all scoped to the returned user's id (issue #28)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user_id = session_codec.verify(token) if token else None
    user = user_repo.find_by_id(user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _require_user_id(user: UserRecord) -> int:
    """A signed-in `UserRecord` always has an id — it only ever comes from a row
    already persisted (`get_current_user`'s `find_by_id`). Narrows `int | None` to
    `int` once for every user-scoped repository provider below."""
    assert user.id is not None
    return user.id


def get_activity_source(
    user: UserRecord = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    encryption_config: EncryptionConfig = Depends(get_encryption_config),
) -> GarminSessionClient:
    """Each user's own Garmin session (issue #30, ADR-0006), never the old shared
    `GarminConfig`/`GARMIN_EMAIL`/`GARMIN_PASSWORD` — those are retired for
    authenticated requests. Prefers the user's stored session tokens (no repeat
    login, no risk of a fresh MFA prompt); a missing/rejected session falls back to
    a password login, persisting whatever session comes out of it so the next call
    can resume from there again."""
    if user.garmin_email is None or user.garmin_password_encrypted is None:
        raise HTTPException(status_code=400, detail="Connect your Garmin account first")

    key = encryption_config.secret_encryption_key
    password = decrypt(user.garmin_password_encrypted, key)
    session_tokens = (
        decrypt(user.garmin_session_encrypted, key) if user.garmin_session_encrypted else None
    )

    client = GarminActivityClient(
        email=user.garmin_email, password=password, tokenstore=session_tokens or ""
    )
    try:
        client.login()
    except GarminConnectAuthenticationError as exc:
        # Could be an expired/rejected session, a changed Garmin password, or (since no
        # prompt_mfa/return_on_mfa is passed here) a fresh MFA challenge — garminconnect
        # doesn't distinguish these outcomes, so the message stays generic rather than
        # guessing which one it was.
        raise HTTPException(
            status_code=400,
            detail="Your Garmin session needs to be reconnected — connect your account again",
        ) from exc

    user_repo.set_garmin_session(_require_user_id(user), encrypt(client.dump_session(), key))
    return client


def get_activity_repository(
    session: Session = Depends(_get_db_session),
    user: UserRecord = Depends(get_current_user),
) -> ActivityRepository:
    return SqlAlchemyActivityRepository(session, _require_user_id(user))


def get_rapport_repository(
    session: Session = Depends(_get_db_session),
    user: UserRecord = Depends(get_current_user),
) -> RapportRepository:
    return SqlAlchemyRapportRepository(session, _require_user_id(user))


def get_objectif_repository(
    session: Session = Depends(_get_db_session),
    user: UserRecord = Depends(get_current_user),
) -> ObjectifRepository:
    return SqlAlchemyObjectifRepository(session, _require_user_id(user))


def get_plan_repository(
    session: Session = Depends(_get_db_session),
    user: UserRecord = Depends(get_current_user),
) -> PlanRepository:
    return SqlAlchemyPlanRepository(session, _require_user_id(user))


def get_garmin_push_client(
    source: GarminSessionClient = Depends(get_activity_source),
) -> GarminPushClient:
    """The same logged-in `GarminActivityClient` as `get_activity_source`.

    Depending on `get_activity_source` (rather than constructing a second client) lets
    FastAPI's per-request dependency caching reuse the one already-authenticated
    session instead of logging in twice — see issue #5's "reuse the auth from #1".
    `GarminSessionClient` already includes `GarminPushClient`'s methods, so no cast
    is needed — the `isinstance` check below only exists because a test overriding
    `get_activity_source` with a narrower fake (only `ActivitySource`-shaped) isn't
    caught by mypy, since this repo's CI doesn't type-check `tests/`; it turns that
    mistake into a clear assertion right at this seam instead of a confusing
    `AttributeError` buried inside a later `push_workout`/`delete_workout` call.
    """
    assert isinstance(source, GarminSessionClient), (
        f"{source!r} doesn't implement push_workout/delete_workout — "
        "get_activity_source must be overridden with something GarminSessionClient-shaped."
    )
    return source


def get_llm_client(
    user: UserRecord = Depends(get_current_user),
    encryption_config: EncryptionConfig = Depends(get_encryption_config),
) -> LLMClient:
    """Each user's own Gemini key (issue #29), never the old shared global one —
    `LlmConfig`/`GEMINI_API_KEY` are retired for authenticated requests."""
    if user.gemini_api_key_encrypted is None:
        raise HTTPException(status_code=400, detail="Connect your Gemini API key first")
    api_key = decrypt(user.gemini_api_key_encrypted, encryption_config.secret_encryption_key)
    return GeminiLLMClient(api_key=api_key)


def _to_response(activity: ActivityRecord) -> ActivityResponse:
    return ActivityResponse(
        garmin_activity_id=activity.garmin_activity_id,
        sport=activity.sport,
        started_at=activity.started_at,
        duration_seconds=activity.duration_seconds,
        distance_meters=activity.distance_meters,
        average_heart_rate=activity.average_heart_rate,
    )


class SyncResponse(BaseModel):
    imported_count: int


class ActivityResponse(BaseModel):
    garmin_activity_id: str
    sport: str
    started_at: datetime
    duration_seconds: float
    distance_meters: float | None
    average_heart_rate: float | None


class RapportResponse(BaseModel):
    garmin_activity_id: str
    strengths: str
    improvements: str
    generated_at: datetime
    completed_as_planned: bool
    perceived_effort: str
    flag: str


def _to_rapport_response(rapport: RapportRecord) -> RapportResponse:
    return RapportResponse(
        garmin_activity_id=rapport.garmin_activity_id,
        strengths=rapport.strengths,
        improvements=rapport.improvements,
        generated_at=rapport.generated_at,
        completed_as_planned=rapport.completed_as_planned,
        perceived_effort=rapport.perceived_effort,
        flag=rapport.flag,
    )


class ObjectifRequest(BaseModel):
    sport: str
    target_distance_meters: float
    target_date: date
    target_time_seconds: float | None = None


class ObjectifResponse(BaseModel):
    id: int
    sport: str
    target_distance_meters: float
    target_date: date
    target_time_seconds: float | None


def _to_objectif_response(objectif: ObjectifRecord) -> ObjectifResponse:
    assert objectif.id is not None
    return ObjectifResponse(
        id=objectif.id,
        sport=objectif.sport,
        target_distance_meters=objectif.target_distance_meters,
        target_date=objectif.target_date,
        target_time_seconds=objectif.target_time_seconds,
    )


class SeanceResponse(BaseModel):
    id: int
    week_start: date
    phase: str
    detail: str
    scheduled_date: date | None
    seance_type: str | None
    distance_meters: float | None
    theme: str | None
    week_volume_meters: float
    status: str
    garmin_activity_id: str | None
    garmin_workout_id: str | None


def _to_seance_response(seance: SeanceRecord) -> SeanceResponse:
    assert seance.id is not None
    return SeanceResponse(
        id=seance.id,
        week_start=seance.week_start,
        phase=seance.phase,
        detail=seance.detail,
        scheduled_date=seance.scheduled_date,
        seance_type=seance.seance_type,
        distance_meters=seance.distance_meters,
        theme=seance.theme,
        week_volume_meters=seance.week_volume_meters,
        status=seance.status,
        garmin_activity_id=seance.garmin_activity_id,
        garmin_workout_id=seance.garmin_workout_id,
    )


class PlanResponse(BaseModel):
    id: int
    objectif_id: int
    seances: list[SeanceResponse]


def _to_plan_response(plan: PlanRecord) -> PlanResponse:
    assert plan.id is not None
    return PlanResponse(
        id=plan.id,
        objectif_id=plan.objectif_id,
        seances=[_to_seance_response(s) for s in plan.seances],
    )


class SeanceUpdateRequest(BaseModel):
    seance_type: str | None = None
    distance_meters: float | None = None
    status: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class MeResponse(BaseModel):
    email: str


@app.get("/auth/google/login")
def google_login(
    verifier: GoogleIdentityVerifier = Depends(get_google_identity_verifier),
    auth_config: AuthConfig = Depends(get_auth_config),
) -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(
        verifier.authorization_url(auth_config.google_oauth_redirect_uri, state=state)
    )
    response.set_cookie(
        OAUTH_STATE_COOKIE_NAME,
        state,
        httponly=True,
        samesite="lax",
        max_age=OAUTH_STATE_MAX_AGE_SECONDS,
    )
    return response


@app.get("/auth/google/callback")
def google_callback(
    request: Request,
    code: str,
    state: str,
    verifier: GoogleIdentityVerifier = Depends(get_google_identity_verifier),
    user_repo: UserRepository = Depends(get_user_repository),
    session_codec: SessionCodec = Depends(get_session_codec),
    auth_config: AuthConfig = Depends(get_auth_config),
) -> RedirectResponse:
    def _login_error(error: str) -> RedirectResponse:
        """Sends the browser back to the login screen with a message it can render,
        rather than a raw API error (issue #26: "rejected with a clear message")."""
        response = RedirectResponse(f"{auth_config.frontend_base_url}/login?error={error}")
        response.delete_cookie(OAUTH_STATE_COOKIE_NAME)
        return response

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE_NAME)
    if expected_state is None or expected_state != state:
        return _login_error("invalid_state")

    try:
        identity = verifier.exchange_code(code, auth_config.google_oauth_redirect_uri)
    except GoogleAuthError:
        return _login_error("google_auth_failed")

    if not user_repo.is_email_allowed(identity.email):
        return _login_error("not_invited")

    user = user_repo.find_by_google_subject(identity.subject)
    if user is None:
        user = user_repo.create(identity.subject, identity.email)
    assert user.id is not None

    response = RedirectResponse(auth_config.frontend_base_url)
    response.delete_cookie(OAUTH_STATE_COOKIE_NAME)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_codec.create(user.id),
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    return response


@app.post("/auth/logout")
def logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/auth/me", response_model=MeResponse)
def get_me(user: UserRecord = Depends(get_current_user)) -> MeResponse:
    return MeResponse(email=user.email)


class SetGeminiApiKeyRequest(BaseModel):
    api_key: str


@app.post("/users/me/gemini-key", status_code=204)
def set_gemini_api_key(
    body: SetGeminiApiKeyRequest,
    user: UserRecord = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    encryption_config: EncryptionConfig = Depends(get_encryption_config),
) -> Response:
    """Self-service Gemini key onboarding (issue #29) — validated with a real call
    before being stored encrypted, so a typo is caught immediately rather than at the
    next rapport generation. Resubmitting replaces the previous key (rotation)."""
    if not validate_gemini_api_key(body.api_key):
        raise HTTPException(status_code=400, detail="Invalid Gemini API key")

    encrypted = encrypt(body.api_key, encryption_config.secret_encryption_key)
    user_repo.set_gemini_api_key(_require_user_id(user), encrypted)
    return Response(status_code=204)


class ConnectGarminRequest(BaseModel):
    email: str
    password: str


class GarminMfaCodeRequest(BaseModel):
    pending_login_id: str
    mfa_code: str


class ConnectGarminResponse(BaseModel):
    status: Literal["connected", "mfa_required"]
    pending_login_id: str | None = None


def _store_garmin_login(
    user_id: int,
    outcome: GarminLoginSuccess,
    user_repo: UserRepository,
    encryption_config: EncryptionConfig,
) -> None:
    key = encryption_config.secret_encryption_key
    user_repo.set_garmin_credentials(user_id, outcome.email, encrypt(outcome.password, key))
    user_repo.set_garmin_session(user_id, encrypt(outcome.session_tokens, key))


@app.post("/users/me/garmin-credentials", response_model=ConnectGarminResponse)
def connect_garmin_account(
    body: ConnectGarminRequest,
    user: UserRecord = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    encryption_config: EncryptionConfig = Depends(get_encryption_config),
    pending_logins: PendingGarminLoginStore = Depends(get_pending_garmin_login_store),
) -> ConnectGarminResponse:
    """Self-service Garmin onboarding, step 1 (issue #30, ADR-0006) —
    `python-garminconnect` has no OAuth, so this is the user's real Garmin
    email/password. Nothing is stored on a rejected login; a login that needs MFA
    stores nothing yet either — it's completed by `complete_garmin_account_mfa`
    below, which is the only path that reaches `_store_garmin_login` for that case."""
    user_id = _require_user_id(user)
    try:
        outcome = initiate_garmin_login(body.email, body.password, pending_logins, user_id)
    except GarminAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if isinstance(outcome, GarminMfaRequired):
        return ConnectGarminResponse(
            status="mfa_required", pending_login_id=outcome.pending_login_id
        )

    _store_garmin_login(user_id, outcome, user_repo, encryption_config)
    return ConnectGarminResponse(status="connected")


@app.post("/users/me/garmin-credentials/mfa", response_model=ConnectGarminResponse)
def complete_garmin_account_mfa(
    body: GarminMfaCodeRequest,
    user: UserRecord = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    encryption_config: EncryptionConfig = Depends(get_encryption_config),
    pending_logins: PendingGarminLoginStore = Depends(get_pending_garmin_login_store),
) -> ConnectGarminResponse:
    """Self-service Garmin onboarding, step 2 (issue #30) — completes the login
    `connect_garmin_account` started, resuming the same in-process pending login by
    id (`PendingGarminLoginStore`)."""
    user_id = _require_user_id(user)
    try:
        outcome = complete_garmin_mfa(body.pending_login_id, body.mfa_code, pending_logins, user_id)
    except GarminAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _store_garmin_login(user_id, outcome, user_repo, encryption_config)
    return ConnectGarminResponse(status="connected")


@app.post("/sync", response_model=SyncResponse)
def trigger_sync(
    source: ActivitySource = Depends(get_activity_source),
    repo: ActivityRepository = Depends(get_activity_repository),
    objectif_repo: ObjectifRepository = Depends(get_objectif_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
    garmin: GarminPushClient = Depends(get_garmin_push_client),
    llm: LLMClient = Depends(get_llm_client),
) -> SyncResponse:
    orchestrator = SyncOrchestrator(source, repo, objectif_repo, plan_repo, garmin, llm)
    result = orchestrator.run(today=date.today())
    return SyncResponse(imported_count=result.imported_count)


@app.get("/activities", response_model=list[ActivityResponse])
def list_activities(
    since: date | None = None,
    until: date | None = None,
    repo: ActivityRepository = Depends(get_activity_repository),
) -> list[ActivityResponse]:
    activities = repo.list_activities(DateRange(since=since, until=until))
    return [_to_response(a) for a in activities]


@app.get("/activities/{garmin_activity_id}", response_model=ActivityResponse)
def get_activity(
    garmin_activity_id: str,
    repo: ActivityRepository = Depends(get_activity_repository),
) -> ActivityResponse:
    activity = repo.get_activity(garmin_activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return _to_response(activity)


@app.post("/activities/{garmin_activity_id}/rapport", response_model=RapportResponse)
def generate_activity_rapport(
    garmin_activity_id: str,
    repo: ActivityRepository = Depends(get_activity_repository),
    rapport_repo: RapportRepository = Depends(get_rapport_repository),
    objectif_repo: ObjectifRepository = Depends(get_objectif_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
    garmin: GarminPushClient = Depends(get_garmin_push_client),
    llm: LLMClient = Depends(get_llm_client),
) -> RapportResponse:
    orchestrator = RapportOrchestrator(
        repo, rapport_repo, objectif_repo, plan_repo, garmin, llm, RECENT_RAPPORTS_FOR_ADJUSTMENT
    )
    rapport = orchestrator.generate_for_activity(garmin_activity_id, today=date.today())
    if rapport is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return _to_rapport_response(rapport)


@app.get("/activities/{garmin_activity_id}/rapport", response_model=RapportResponse)
def get_activity_rapport(
    garmin_activity_id: str,
    rapport_repo: RapportRepository = Depends(get_rapport_repository),
) -> RapportResponse:
    rapport = rapport_repo.get_for_activity(garmin_activity_id)
    if rapport is None:
        raise HTTPException(status_code=404, detail="Rapport not found")
    return _to_rapport_response(rapport)


@app.post("/objectif", response_model=PlanResponse)
def create_objectif(
    body: ObjectifRequest,
    activity_repo: ActivityRepository = Depends(get_activity_repository),
    objectif_repo: ObjectifRepository = Depends(get_objectif_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
    llm: LLMClient = Depends(get_llm_client),
) -> PlanResponse:
    """Creates an `Objectif` and generates its `Plan` (ADR-0001, issue #4)."""
    today = date.today()
    objectif = objectif_repo.save(
        ObjectifRecord(
            id=None,
            sport=body.sport,
            target_distance_meters=body.target_distance_meters,
            target_date=body.target_date,
            target_time_seconds=body.target_time_seconds,
            created_at=datetime.now(),
        )
    )
    assert objectif.id is not None

    current_weekly_volume = estimate_current_weekly_volume(
        activity_repo.list_activities(), today=today
    )
    seances = generate_plan_seances(
        objectif, llm=llm, today=today, current_weekly_volume_meters=current_weekly_volume
    )
    plan = plan_repo.save(
        PlanRecord(id=None, objectif_id=objectif.id, created_at=datetime.now(), seances=seances)
    )
    return _to_plan_response(plan)


@app.get("/objectif", response_model=ObjectifResponse)
def get_active_objectif(
    objectif_repo: ObjectifRepository = Depends(get_objectif_repository),
) -> ObjectifResponse:
    objectif = objectif_repo.get_active()
    if objectif is None:
        raise HTTPException(status_code=404, detail="No active objectif")
    return _to_objectif_response(objectif)


@app.get("/plan", response_model=PlanResponse)
def get_active_plan(
    plan_repo: PlanRepository = Depends(get_plan_repository),
) -> PlanResponse:
    plan = plan_repo.get_active()
    if plan is None:
        raise HTTPException(status_code=404, detail="No active plan")
    return _to_plan_response(plan)


@app.patch("/plan/seances/{seance_id}", response_model=SeanceResponse)
def update_seance(
    seance_id: int,
    body: SeanceUpdateRequest,
    plan_repo: PlanRepository = Depends(get_plan_repository),
) -> SeanceResponse:
    """Manual edit of a séance from the dashboard/agenda (issue #4)."""
    plan = plan_repo.get_active()
    seance = next((s for s in (plan.seances if plan else []) if s.id == seance_id), None)
    if seance is None:
        raise HTTPException(status_code=404, detail="Seance not found")

    updates = body.model_dump(exclude_unset=True)
    updated = replace(seance, **updates)
    plan_repo.update_seances([updated])
    return _to_seance_response(updated)
