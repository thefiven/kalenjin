from datetime import date, datetime

import pytest
from sqlalchemy.orm import Session

from kalenjin.db.repository import SqlAlchemyObjectifRepository, SqlAlchemyPlanRepository
from kalenjin.plan.domain import ObjectifRecord, PlanRecord, SeanceRecord

pytestmark = pytest.mark.integration


def _objectif(target_date: date = date(2026, 6, 1)) -> ObjectifRecord:
    return ObjectifRecord(
        id=None,
        sport="running",
        target_distance_meters=10_000,
        target_date=target_date,
        target_time_seconds=None,
        created_at=datetime(2026, 1, 1, 8, 0),
    )


def _detailed_seance(week_start: date, scheduled_date: date) -> SeanceRecord:
    return SeanceRecord(
        id=None,
        plan_id=None,
        week_start=week_start,
        phase="base",
        detail="detailed",
        scheduled_date=scheduled_date,
        seance_type="easy",
        distance_meters=5000,
        theme=None,
        week_volume_meters=20_000,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def _coarse_seance(week_start: date) -> SeanceRecord:
    return SeanceRecord(
        id=None,
        plan_id=None,
        week_start=week_start,
        phase="base",
        detail="coarse",
        scheduled_date=None,
        seance_type=None,
        distance_meters=None,
        theme="Base — ~20km target volume",
        week_volume_meters=20_000,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


class TestObjectifRepository:
    def test_get_active_returns_none_when_no_objectif_exists(self, db_session: Session) -> None:
        repo = SqlAlchemyObjectifRepository(db_session)

        assert repo.get_active() is None

    def test_save_assigns_an_id_and_get_active_returns_it(self, db_session: Session) -> None:
        repo = SqlAlchemyObjectifRepository(db_session)

        saved = repo.save(_objectif())

        assert saved.id is not None
        active = repo.get_active()
        assert active is not None
        assert active.id == saved.id
        assert active.target_distance_meters == 10_000

    def test_get_active_returns_the_most_recently_created_objectif(
        self, db_session: Session
    ) -> None:
        repo = SqlAlchemyObjectifRepository(db_session)
        repo.save(_objectif(target_date=date(2026, 6, 1)))
        second = repo.save(_objectif(target_date=date(2026, 9, 1)))

        active = repo.get_active()

        assert active is not None
        assert active.id == second.id


class TestPlanRepository:
    def test_save_persists_the_plan_and_its_seances(self, db_session: Session) -> None:
        objectif_repo = SqlAlchemyObjectifRepository(db_session)
        plan_repo = SqlAlchemyPlanRepository(db_session)
        objectif = objectif_repo.save(_objectif())

        assert objectif.id is not None
        plan = plan_repo.save(
            PlanRecord(
                id=None,
                objectif_id=objectif.id,
                created_at=datetime(2026, 1, 1, 8, 0),
                seances=[
                    _detailed_seance(date(2026, 1, 5), date(2026, 1, 5)),
                    _coarse_seance(date(2026, 1, 12)),
                ],
            )
        )

        assert plan.id is not None
        assert len(plan.seances) == 2
        assert all(s.id is not None for s in plan.seances)
        assert all(s.plan_id == plan.id for s in plan.seances)

    def test_get_active_returns_the_plan_for_the_most_recent_objectif(
        self, db_session: Session
    ) -> None:
        objectif_repo = SqlAlchemyObjectifRepository(db_session)
        plan_repo = SqlAlchemyPlanRepository(db_session)
        objectif = objectif_repo.save(_objectif())
        assert objectif.id is not None
        plan_repo.save(
            PlanRecord(
                id=None,
                objectif_id=objectif.id,
                created_at=datetime(2026, 1, 1, 8, 0),
                seances=[_detailed_seance(date(2026, 1, 5), date(2026, 1, 5))],
            )
        )

        active = plan_repo.get_active()

        assert active is not None
        assert active.objectif_id == objectif.id
        assert len(active.seances) == 1

    def test_update_seances_updates_fields_in_place(self, db_session: Session) -> None:
        objectif_repo = SqlAlchemyObjectifRepository(db_session)
        plan_repo = SqlAlchemyPlanRepository(db_session)
        objectif = objectif_repo.save(_objectif())
        assert objectif.id is not None
        plan = plan_repo.save(
            PlanRecord(
                id=None,
                objectif_id=objectif.id,
                created_at=datetime(2026, 1, 1, 8, 0),
                seances=[_detailed_seance(date(2026, 1, 5), date(2026, 1, 5))],
            )
        )
        seance = plan.seances[0]

        from dataclasses import replace

        plan_repo.update_seances([replace(seance, seance_type="easy", distance_meters=1234)])

        active = plan_repo.get_active()
        assert active is not None
        assert active.seances[0].distance_meters == 1234

    def test_replace_seances_removes_and_inserts(self, db_session: Session) -> None:
        objectif_repo = SqlAlchemyObjectifRepository(db_session)
        plan_repo = SqlAlchemyPlanRepository(db_session)
        objectif = objectif_repo.save(_objectif())
        assert objectif.id is not None
        plan = plan_repo.save(
            PlanRecord(
                id=None,
                objectif_id=objectif.id,
                created_at=datetime(2026, 1, 1, 8, 0),
                seances=[_coarse_seance(date(2026, 1, 12))],
            )
        )
        coarse = plan.seances[0]
        assert coarse.id is not None
        new_seance = _detailed_seance(date(2026, 1, 12), date(2026, 1, 12))

        inserted = plan_repo.replace_seances([coarse.id], [replace_plan_id(new_seance, plan.id)])

        assert len(inserted) == 1
        assert inserted[0].id is not None
        active = plan_repo.get_active()
        assert active is not None
        assert [s.id for s in active.seances] == [inserted[0].id]


def replace_plan_id(seance: SeanceRecord, plan_id: int | None) -> SeanceRecord:
    from dataclasses import replace

    return replace(seance, plan_id=plan_id)
