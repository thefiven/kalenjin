from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from kalenjin.cli import prompt_mfa_via_console
from kalenjin.config.settings import Settings
from kalenjin.db.repository import SqlAlchemyActivityRepository
from kalenjin.db.session import make_engine, make_session_factory, session_scope
from kalenjin.garmin.client import GarminActivityClient
from kalenjin.sync.domain import ActivityRecord, ActivityRepository, ActivitySource
from kalenjin.sync.service import sync_activities

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


def get_activity_repository() -> Iterator[ActivityRepository]:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        yield SqlAlchemyActivityRepository(session)


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sync", response_model=SyncResponse)
def trigger_sync(
    source: ActivitySource = Depends(get_activity_source),
    repo: ActivityRepository = Depends(get_activity_repository),
) -> SyncResponse:
    result = sync_activities(source, repo, today=date.today())
    return SyncResponse(imported_count=result.imported_count)


@app.get("/activities", response_model=list[ActivityResponse])
def list_activities(
    since: date | None = None,
    until: date | None = None,
    repo: ActivityRepository = Depends(get_activity_repository),
) -> list[ActivityResponse]:
    activities = repo.list_activities(since=since, until=until)
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
