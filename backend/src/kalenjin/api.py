from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from functools import lru_cache

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from kalenjin.cli import prompt_mfa_via_console
from kalenjin.config.settings import Settings
from kalenjin.db.repository import SqlAlchemyActivityRepository
from kalenjin.db.session import make_engine, make_session_factory, session_scope
from kalenjin.garmin.client import GarminActivityClient
from kalenjin.sync.domain import ActivityRepository, ActivitySource
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


class SyncResponse(BaseModel):
    imported_count: int


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
