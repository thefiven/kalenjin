import json
from datetime import date, datetime, timedelta
from itertools import pairwise

import pytest

from kalenjin.plan.domain import ObjectifRecord
from kalenjin.plan.generation import (
    PlanGenerationError,
    estimate_current_weekly_volume,
    generate_plan_seances,
)
from kalenjin.sync.domain import ActivityRecord
from support.fakes import FakeLLMClient

MONDAY = date(2026, 1, 5)


def _objectif(target_date: date, target_distance_meters: float = 10_000) -> ObjectifRecord:
    return ObjectifRecord(
        id=1,
        sport="running",
        target_distance_meters=target_distance_meters,
        target_date=target_date,
        target_time_seconds=None,
        created_at=datetime(2026, 1, 1, 8, 0),
    )


def _activity(days_ago: int, distance: float, today: date) -> ActivityRecord:
    started = datetime.combine(today - timedelta(days=days_ago), datetime.min.time())
    return ActivityRecord(
        garmin_activity_id=f"a{days_ago}",
        sport="running",
        started_at=started,
        duration_seconds=1800.0,
        distance_meters=distance,
        average_heart_rate=150.0,
        raw_payload={},
    )


def _week_response(sessions: list[dict[str, object]]) -> str:
    return json.dumps(sessions)


class TestEstimateCurrentWeeklyVolume:
    def test_averages_distance_over_the_lookback_window(self) -> None:
        activities = [
            _activity(days_ago=1, distance=10_000, today=MONDAY),
            _activity(days_ago=8, distance=10_000, today=MONDAY),
        ]

        volume = estimate_current_weekly_volume(activities, today=MONDAY, weeks=2)

        assert volume == pytest.approx(10_000)

    def test_falls_back_to_a_conservative_default_when_there_is_no_history(self) -> None:
        volume = estimate_current_weekly_volume([], today=MONDAY, weeks=4)

        assert volume > 0

    def test_ignores_activities_outside_the_lookback_window(self) -> None:
        activities = [_activity(days_ago=30, distance=50_000, today=MONDAY)]

        volume = estimate_current_weekly_volume(activities, today=MONDAY, weeks=4)

        assert volume != pytest.approx(50_000 / 4)


class TestGeneratePlanSeances:
    def test_near_term_weeks_are_detailed_and_far_term_weeks_are_coarse(self) -> None:
        llm = FakeLLMClient(
            _week_response(
                [
                    {"day_offset": 0, "type": "easy", "distance_meters": 5000},
                    {"day_offset": 3, "type": "easy", "distance_meters": 5000},
                    {"day_offset": 6, "type": "long_run", "distance_meters": 6000},
                ]
            )
        )
        objectif = _objectif(target_date=MONDAY + timedelta(weeks=8))

        seances = generate_plan_seances(
            objectif, llm=llm, today=MONDAY, current_weekly_volume_meters=16_000
        )

        first_week_seances = [s for s in seances if s.week_start == MONDAY]
        later_week_seances = [s for s in seances if s.week_start == MONDAY + timedelta(weeks=7)]
        assert all(s.detail == "detailed" for s in first_week_seances)
        assert len(later_week_seances) == 1
        assert later_week_seances[0].detail == "coarse"
        assert later_week_seances[0].theme is not None

    def test_detailed_seances_get_a_concrete_scheduled_date(self) -> None:
        llm = FakeLLMClient(
            _week_response(
                [
                    {"day_offset": 0, "type": "easy", "distance_meters": 5000},
                    {"day_offset": 6, "type": "long_run", "distance_meters": 6000},
                ]
            )
        )
        objectif = _objectif(target_date=MONDAY + timedelta(weeks=1))

        seances = generate_plan_seances(
            objectif, llm=llm, today=MONDAY, current_weekly_volume_meters=11_000
        )

        scheduled_dates = {s.scheduled_date for s in seances}
        assert MONDAY in scheduled_dates
        assert MONDAY + timedelta(days=6) in scheduled_dates

    def test_rest_days_from_the_llm_are_dropped_rather_than_creating_seances(self) -> None:
        llm = FakeLLMClient(
            _week_response(
                [
                    {"day_offset": 0, "type": "easy", "distance_meters": 11_000},
                    {"day_offset": 1, "type": "rest", "distance_meters": 0},
                ]
            )
        )
        objectif = _objectif(target_date=MONDAY + timedelta(weeks=1))

        seances = generate_plan_seances(
            objectif, llm=llm, today=MONDAY, current_weekly_volume_meters=11_000
        )

        assert all(s.seance_type != "rest" for s in seances)

    def test_falls_back_to_a_deterministic_template_when_the_llm_output_is_not_json(self) -> None:
        llm = FakeLLMClient("not json")
        objectif = _objectif(target_date=MONDAY + timedelta(weeks=1))

        seances = generate_plan_seances(
            objectif, llm=llm, today=MONDAY, current_weekly_volume_meters=20_000
        )

        assert len(seances) > 0
        assert all(s.detail == "detailed" for s in seances)

    def test_falls_back_when_the_llm_exceeds_the_long_run_cap(self) -> None:
        llm = FakeLLMClient(
            _week_response(
                [
                    {"day_offset": 6, "type": "long_run", "distance_meters": 100_000},
                ]
            )
        )
        objectif = _objectif(target_date=MONDAY + timedelta(weeks=1), target_distance_meters=10_000)

        seances = generate_plan_seances(
            objectif, llm=llm, today=MONDAY, current_weekly_volume_meters=20_000
        )

        long_runs = [s for s in seances if s.seance_type == "long_run"]
        assert all((s.distance_meters or 0) <= 20_000 * 0.3 + 1e-6 for s in long_runs)

    def test_falls_back_when_hard_sessions_are_scheduled_back_to_back(self) -> None:
        llm = FakeLLMClient(
            _week_response(
                [
                    {"day_offset": 1, "type": "tempo", "distance_meters": 5000},
                    {"day_offset": 2, "type": "interval", "distance_meters": 5000},
                    {"day_offset": 6, "type": "long_run", "distance_meters": 6000},
                ]
            )
        )
        objectif = _objectif(target_date=MONDAY + timedelta(weeks=1))

        seances = generate_plan_seances(
            objectif, llm=llm, today=MONDAY, current_weekly_volume_meters=16_000
        )

        hard_offsets = sorted(
            (s.scheduled_date - MONDAY).days
            for s in seances
            if s.seance_type in ("tempo", "interval")
        )
        for a, b in pairwise(hard_offsets):
            assert b - a >= 2

    def test_falls_back_when_weekly_total_distance_is_far_from_the_target(self) -> None:
        llm = FakeLLMClient(
            _week_response(
                [
                    {"day_offset": 0, "type": "easy", "distance_meters": 1_000},
                ]
            )
        )
        objectif = _objectif(target_date=MONDAY)

        seances = generate_plan_seances(
            objectif, llm=llm, today=MONDAY, current_weekly_volume_meters=20_000
        )

        total = sum(s.distance_meters or 0 for s in seances)
        assert total == pytest.approx(20_000 * 0.6, rel=0.15)


def test_plan_generation_error_is_raised_by_the_low_level_parser_on_malformed_json() -> None:
    from kalenjin.plan.generation import _parse_and_validate_sessions
    from kalenjin.plan.periodization import Phase, WeekTarget

    week = WeekTarget(
        week_start=MONDAY,
        phase=Phase.BASE,
        target_volume_meters=20_000,
        is_cutback=False,
        long_run_cap_meters=6_000,
        theme="Base — ~20km target volume",
    )

    with pytest.raises(PlanGenerationError):
        _parse_and_validate_sessions("not json", week)
