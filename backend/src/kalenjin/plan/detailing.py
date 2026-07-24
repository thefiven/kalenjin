from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from kalenjin.llm.domain import LLMClient
from kalenjin.plan.domain import ObjectifRecord, SeanceRecord
from kalenjin.plan.generation import DETAIL_HORIZON_DAYS, detail_week
from kalenjin.plan.periodization import Phase, WeekTarget, long_run_cap_for


@dataclass(frozen=True)
class PromotionResult:
    removed_seance_ids: list[int]
    new_seances: list[SeanceRecord]


def promote_due_weeks(
    seances: list[SeanceRecord], objectif: ObjectifRecord, llm: LLMClient, today: date
) -> PromotionResult:
    """Converts coarse weeks entering the detail horizon into concrete séances (ADR-0001).

    Only ever promotes a coarse week's already-committed phase/volume target into
    concrete sessions — it never re-derives that target, so a plan's committed weekly
    volume can't silently drift from what was set at generation time (`generation.py`).
    """
    horizon = today + timedelta(days=DETAIL_HORIZON_DAYS)
    due = [
        seance for seance in seances if seance.detail == "coarse" and seance.week_start < horizon
    ]

    removed_ids: list[int] = []
    new_seances: list[SeanceRecord] = []
    for coarse in due:
        if coarse.id is not None:
            removed_ids.append(coarse.id)
        week = WeekTarget(
            week_start=coarse.week_start,
            phase=Phase(coarse.phase),
            target_volume_meters=coarse.week_volume_meters,
            is_cutback=False,
            long_run_cap_meters=long_run_cap_for(
                coarse.week_volume_meters, objectif.target_distance_meters
            ),
            theme=coarse.theme or "",
        )
        new_seances.extend(detail_week(week, objectif, llm))

    return PromotionResult(removed_seance_ids=removed_ids, new_seances=new_seances)
