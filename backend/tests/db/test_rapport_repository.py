from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from kalenjin.db.repository import SqlAlchemyRapportRepository
from kalenjin.rapport.domain import RapportRecord

pytestmark = pytest.mark.integration


def _rapport(
    activity_id: str,
    strengths: str = "Good pace.",
    improvements: str = "Add strides.",
    generated_at: datetime = datetime(2024, 6, 1, 8, 0),
) -> RapportRecord:
    return RapportRecord(
        garmin_activity_id=activity_id,
        strengths=strengths,
        improvements=improvements,
        generated_at=generated_at,
        completed_as_planned=True,
        perceived_effort="as_expected",
        flag="none",
    )


def test_get_for_activity_returns_none_when_missing(db_session: Session) -> None:
    repo = SqlAlchemyRapportRepository(db_session)

    assert repo.get_for_activity("does-not-exist") is None


def test_save_then_get_for_activity_returns_the_saved_rapport(db_session: Session) -> None:
    repo = SqlAlchemyRapportRepository(db_session)

    repo.save(_rapport("1"))

    rapport = repo.get_for_activity("1")
    assert rapport is not None
    assert rapport.garmin_activity_id == "1"
    assert rapport.strengths == "Good pace."
    assert rapport.improvements == "Add strides."
    assert rapport.generated_at == datetime(2024, 6, 1, 8, 0)


def test_save_replaces_the_existing_rapport_for_the_same_activity(db_session: Session) -> None:
    repo = SqlAlchemyRapportRepository(db_session)
    repo.save(_rapport("1", strengths="First version."))

    repo.save(_rapport("1", strengths="Regenerated version."))

    rapport = repo.get_for_activity("1")
    assert rapport is not None
    assert rapport.strengths == "Regenerated version."
