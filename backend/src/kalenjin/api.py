from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import date, datetime
from functools import lru_cache
from typing import cast

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kalenjin.cli import prompt_mfa_via_console
from kalenjin.config.settings import Settings
from kalenjin.db.repository import (
    SqlAlchemyActivityRepository,
    SqlAlchemyObjectifRepository,
    SqlAlchemyPlanRepository,
    SqlAlchemyRapportRepository,
)
from kalenjin.db.session import make_engine, make_session_factory, session_scope
from kalenjin.garmin.client import GarminActivityClient
from kalenjin.llm.domain import LLMClient
from kalenjin.llm.gemini_client import GeminiLLMClient
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
from kalenjin.sync.domain import ActivityRecord, ActivityRepository, ActivitySource, DateRange
from kalenjin.sync.orchestrator import SyncOrchestrator

RECENT_RAPPORTS_FOR_ADJUSTMENT = 5

app = FastAPI(title="Kalenjin")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # fields are sourced from the environment


def get_activity_source() -> ActivitySource:
    settings = get_settings()
    client = GarminActivityClient(
        email=settings.garmin_email,
        password=settings.garmin_password,
        tokenstore=settings.garmin_tokenstore,
        prompt_mfa=prompt_mfa_via_console,
    )
    client.login()
    return client


def _get_db_session() -> Iterator[Session]:
    """The request's shared unit-of-work seam: every `get_x_repository` provider below
    depends on this same callable, and FastAPI caches a dependency's result for the
    scope of one request — so any two repositories requested in the same endpoint
    share this one session, and can safely cross-reference rows written moments
    earlier in the same not-yet-committed transaction (e.g. `create_objectif` saving a
    Plan that references the Objectif it just saved)."""
    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        yield session


def get_activity_repository(
    session: Session = Depends(_get_db_session),
) -> ActivityRepository:
    return SqlAlchemyActivityRepository(session)


def get_rapport_repository(session: Session = Depends(_get_db_session)) -> RapportRepository:
    return SqlAlchemyRapportRepository(session)


def get_objectif_repository(session: Session = Depends(_get_db_session)) -> ObjectifRepository:
    return SqlAlchemyObjectifRepository(session)


def get_plan_repository(session: Session = Depends(_get_db_session)) -> PlanRepository:
    return SqlAlchemyPlanRepository(session)


def get_garmin_push_client(
    source: ActivitySource = Depends(get_activity_source),
) -> GarminPushClient:
    """The same logged-in `GarminActivityClient` as `get_activity_source`, retyped.

    Depending on `get_activity_source` (rather than constructing a second client) lets
    FastAPI's per-request dependency caching reuse the one already-authenticated
    session instead of logging in twice — see issue #5's "reuse the auth from #1".
    """
    return cast(GarminPushClient, source)


def get_llm_client() -> LLMClient:
    return GeminiLLMClient(api_key=get_settings().gemini_api_key)


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
