from __future__ import annotations

import secrets
from collections.abc import Iterator
from dataclasses import replace
from datetime import date, datetime
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
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
from kalenjin.garmin.connection import (
    Connected,
    GarminConnection,
    GarminNotConnectedError,
    GarminReauthRequiredError,
    MfaRequired,
    UserGarminConnection,
)
from kalenjin.garmin.login import GarminAuthError, PendingGarminLoginStore
from kalenjin.llm.connection import (
    GeminiConnection,
    GeminiInvalidKeyError,
    GeminiNotConnectedError,
    GeminiReauthRequiredError,
    UserGeminiConnection,
)
from kalenjin.plan.domain import (
    ObjectifRecord,
    ObjectifRepository,
    PlanRecord,
    PlanRepository,
    SeanceRecord,
)
from kalenjin.plan.generation import estimate_current_weekly_volume, generate_plan_seances
from kalenjin.rapport.domain import RapportRecord, RapportRepository
from kalenjin.rapport.orchestrator import RapportOrchestrator
from kalenjin.sync.domain import ActivityRecord, ActivityRepository, DateRange
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


def get_garmin_connection(
    user: UserRecord = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    encryption_config: EncryptionConfig = Depends(get_encryption_config),
    pending_logins: PendingGarminLoginStore = Depends(get_pending_garmin_login_store),
) -> GarminConnection:
    return UserGarminConnection(
        _require_user_id(user),
        user_repo,
        encryption_config.secret_encryption_key,
        pending_logins,
    )


def get_gemini_connection(
    user: UserRecord = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    encryption_config: EncryptionConfig = Depends(get_encryption_config),
) -> GeminiConnection:
    return UserGeminiConnection(
        _require_user_id(user), user_repo, encryption_config.secret_encryption_key
    )


def _client_error(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


for _exc_type in (
    GarminNotConnectedError,
    GarminReauthRequiredError,
    GarminAuthError,
    GeminiNotConnectedError,
    GeminiReauthRequiredError,
    GeminiInvalidKeyError,
):
    app.add_exception_handler(_exc_type, _client_error)


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
    body: SetGeminiApiKeyRequest, gemini: GeminiConnection = Depends(get_gemini_connection)
) -> Response:
    """Self-service Gemini key onboarding (issue #29) — validated with a real call
    before being stored encrypted, so a typo is caught immediately rather than at the
    next rapport generation (`GeminiInvalidKeyError`, mapped to a 400 by the handler
    registered above). Resubmitting replaces the previous key (rotation)."""
    gemini.set_key(body.api_key)
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


@app.post("/users/me/garmin-credentials", response_model=ConnectGarminResponse)
def connect_garmin_account(
    body: ConnectGarminRequest,
    garmin: GarminConnection = Depends(get_garmin_connection),
) -> ConnectGarminResponse:
    """Self-service Garmin onboarding, step 1 (issue #30, ADR-0006) —
    `python-garminconnect` has no OAuth, so this is the user's real Garmin
    email/password. Nothing is stored on a rejected login (`GarminAuthError`, mapped
    to a 400 by the handler registered above); a login that needs MFA stores nothing
    yet either — `GarminConnection.complete_mfa` is what finishes that case."""
    outcome = garmin.connect(body.email, body.password)
    if isinstance(outcome, MfaRequired):
        return ConnectGarminResponse(
            status="mfa_required", pending_login_id=outcome.pending_login_id
        )
    assert isinstance(outcome, Connected)
    return ConnectGarminResponse(status="connected")


@app.post("/users/me/garmin-credentials/mfa", response_model=ConnectGarminResponse)
def complete_garmin_account_mfa(
    body: GarminMfaCodeRequest,
    garmin: GarminConnection = Depends(get_garmin_connection),
) -> ConnectGarminResponse:
    """Self-service Garmin onboarding, step 2 (issue #30) — completes the login
    `connect_garmin_account` started, resuming the same in-process pending login by
    id (`PendingGarminLoginStore`, owned internally by `GarminConnection`)."""
    garmin.complete_mfa(body.pending_login_id, body.mfa_code)
    return ConnectGarminResponse(status="connected")


@app.delete("/users/me/garmin-credentials", status_code=204)
def disconnect_garmin_account(
    garmin: GarminConnection = Depends(get_garmin_connection),
) -> Response:
    """Disconnects the user's Garmin account (issue #25 story 18) — sync stops until
    they reconnect. Idempotent: disconnecting an already-disconnected account is a
    204, not an error."""
    garmin.disconnect()
    return Response(status_code=204)


@app.post("/sync", response_model=SyncResponse)
def trigger_sync(
    repo: ActivityRepository = Depends(get_activity_repository),
    objectif_repo: ObjectifRepository = Depends(get_objectif_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
    garmin: GarminConnection = Depends(get_garmin_connection),
    gemini: GeminiConnection = Depends(get_gemini_connection),
) -> SyncResponse:
    session = garmin.session()
    orchestrator = SyncOrchestrator(
        session, repo, objectif_repo, plan_repo, session, gemini.client()
    )
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
    garmin: GarminConnection = Depends(get_garmin_connection),
    gemini: GeminiConnection = Depends(get_gemini_connection),
) -> RapportResponse:
    session = garmin.session()
    orchestrator = RapportOrchestrator(
        repo,
        rapport_repo,
        objectif_repo,
        plan_repo,
        session,
        gemini.client(),
        RECENT_RAPPORTS_FOR_ADJUSTMENT,
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
    gemini: GeminiConnection = Depends(get_gemini_connection),
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
        objectif,
        llm=gemini.client(),
        today=today,
        current_weekly_volume_meters=current_weekly_volume,
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
