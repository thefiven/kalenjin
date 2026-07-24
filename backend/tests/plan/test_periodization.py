from datetime import date
from itertools import pairwise

import pytest

from kalenjin.plan.periodization import Phase, compute_week_targets

MONDAY = date(2026, 1, 5)


def test_raises_when_target_date_is_before_today() -> None:
    with pytest.raises(ValueError):
        compute_week_targets(
            target_distance_meters=10_000,
            target_date=date(2026, 1, 1),
            today=MONDAY,
            current_weekly_volume_meters=20_000,
        )


def test_raises_when_current_weekly_volume_is_not_positive() -> None:
    with pytest.raises(ValueError):
        compute_week_targets(
            target_distance_meters=10_000,
            target_date=date(2026, 4, 1),
            today=MONDAY,
            current_weekly_volume_meters=0,
        )


def test_covers_every_monday_aligned_week_up_to_and_including_the_goal_week() -> None:
    weeks = compute_week_targets(
        target_distance_meters=10_000,
        target_date=date(2026, 1, 26),  # 4th Monday out
        today=MONDAY,
        current_weekly_volume_meters=20_000,
    )

    assert [w.week_start for w in weeks] == [
        date(2026, 1, 5),
        date(2026, 1, 12),
        date(2026, 1, 19),
        date(2026, 1, 26),
    ]


def test_a_short_race_gets_one_taper_week() -> None:
    weeks = compute_week_targets(
        target_distance_meters=10_000,  # 10K
        target_date=date(2026, 1, 26),
        today=MONDAY,
        current_weekly_volume_meters=20_000,
    )

    assert [w.phase for w in weeks[-1:]] == [Phase.TAPER]
    assert weeks[-2].phase != Phase.TAPER


def test_a_half_marathon_gets_two_taper_weeks() -> None:
    weeks = compute_week_targets(
        target_distance_meters=21_097,
        target_date=date(2026, 3, 30),
        today=MONDAY,
        current_weekly_volume_meters=20_000,
    )

    assert [w.phase for w in weeks[-2:]] == [Phase.TAPER, Phase.TAPER]
    assert weeks[-3].phase != Phase.TAPER


def test_a_marathon_gets_three_taper_weeks() -> None:
    weeks = compute_week_targets(
        target_distance_meters=42_195,
        target_date=date(2026, 6, 29),
        today=MONDAY,
        current_weekly_volume_meters=20_000,
    )

    assert [w.phase for w in weeks[-3:]] == [Phase.TAPER, Phase.TAPER, Phase.TAPER]
    assert weeks[-4].phase != Phase.TAPER


def test_phases_progress_in_order_base_then_build_then_peak_then_taper() -> None:
    weeks = compute_week_targets(
        target_distance_meters=42_195,
        target_date=date(2026, 6, 29),
        today=MONDAY,
        current_weekly_volume_meters=20_000,
    )

    phases_in_order_of_first_appearance = list(dict.fromkeys(w.phase for w in weeks))
    assert phases_in_order_of_first_appearance == [
        Phase.BASE,
        Phase.BUILD,
        Phase.PEAK,
        Phase.TAPER,
    ]


def test_volume_never_grows_more_than_ten_percent_week_over_week_outside_cutback_and_taper() -> (
    None
):
    weeks = compute_week_targets(
        target_distance_meters=42_195,
        target_date=date(2026, 6, 29),
        today=MONDAY,
        current_weekly_volume_meters=20_000,
    )

    for previous, current in pairwise(weeks):
        if current.is_cutback or current.phase == Phase.TAPER:
            continue
        assert current.target_volume_meters <= previous.target_volume_meters * 1.10 + 1e-6


def test_every_fourth_non_taper_week_is_a_cutback_with_reduced_volume() -> None:
    weeks = compute_week_targets(
        target_distance_meters=42_195,
        target_date=date(2026, 6, 29),
        today=MONDAY,
        current_weekly_volume_meters=20_000,
    )
    non_taper = [w for w in weeks if w.phase != Phase.TAPER]

    assert non_taper[3].is_cutback
    assert non_taper[3].target_volume_meters < non_taper[2].target_volume_meters
    assert not non_taper[2].is_cutback


def test_taper_weeks_reduce_volume_below_the_peak() -> None:
    weeks = compute_week_targets(
        target_distance_meters=42_195,
        target_date=date(2026, 6, 29),
        today=MONDAY,
        current_weekly_volume_meters=20_000,
    )
    last_non_taper = next(w for w in reversed(weeks) if w.phase != Phase.TAPER)
    taper_weeks = [w for w in weeks if w.phase == Phase.TAPER]

    for taper_week in taper_weeks:
        assert taper_week.target_volume_meters < last_non_taper.target_volume_meters
    assert taper_weeks[-1].target_volume_meters < taper_weeks[0].target_volume_meters


def test_long_run_cap_is_thirty_percent_of_weekly_volume_when_below_the_absolute_ceiling() -> None:
    weeks = compute_week_targets(
        target_distance_meters=10_000,
        target_date=date(2026, 1, 26),
        today=MONDAY,
        current_weekly_volume_meters=20_000,
    )

    first_week = weeks[0]
    assert first_week.long_run_cap_meters == pytest.approx(first_week.target_volume_meters * 0.3)


def test_long_run_cap_is_bounded_by_an_absolute_ceiling_for_marathon_distance() -> None:
    weeks = compute_week_targets(
        target_distance_meters=42_195,
        target_date=date(2026, 6, 29),
        today=MONDAY,
        current_weekly_volume_meters=100_000,  # deliberately huge, so 30% would exceed the ceiling
    )

    assert all(w.long_run_cap_meters <= 32_000 for w in weeks)
