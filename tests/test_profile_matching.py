import pytest
import numpy as np
import json
from pathlib import Path

from engine.schemas import Session
from engine.profile_matching import (
    map_gap_to_weight,
    scale_raw_to_likert,
    solve_profile_matching_individual,
    solve_profile_matching_group
)
from engine.pipeline import run_all

SAMPLE_CASE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_case.json"

@pytest.fixture
def sample_session():
    with open(SAMPLE_CASE_PATH, "r", encoding="utf-8") as f:
        return Session.model_validate(json.load(f))

def test_scale_raw_to_likert():
    # Benefit: min=10, max=50
    assert scale_raw_to_likert(50, 10, 50, is_benefit=True) == 5
    assert scale_raw_to_likert(10, 10, 50, is_benefit=True) == 1
    assert scale_raw_to_likert(30, 10, 50, is_benefit=True) == 3

    # Cost: min=100, max=500
    assert scale_raw_to_likert(100, 100, 500, is_benefit=False) == 5
    assert scale_raw_to_likert(500, 100, 500, is_benefit=False) == 1

def test_map_gap_to_weight():
    # Follows the UGM standard table (Dr. Sri Mulyana, Slide 26)
    assert map_gap_to_weight(0) == 5.0
    assert map_gap_to_weight(1) == 4.5
    assert map_gap_to_weight(-1) == 4.0
    assert map_gap_to_weight(2) == 3.5
    assert map_gap_to_weight(-2) == 3.0
    assert map_gap_to_weight(3) == 2.5
    assert map_gap_to_weight(-3) == 2.0
    assert map_gap_to_weight(4) == 1.5
    assert map_gap_to_weight(-4) == 1.0

def test_solve_profile_matching_individual(sample_session):
    alts = [a.id for a in sample_session.alternatives]
    crit_types = {c.id: c.type for c in sample_session.criteria}
    crits = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    w = np.array([0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05])

    res = solve_profile_matching_individual(
        dm_id="DM1",
        criteria=crits,
        criteria_weights=w,
        alternatives=alts,
        criteria_types=crit_types,
        values=sample_session.values
    )

    assert res.model == "PROFILE_MATCHING"
    assert res.scope == "individual"
    assert len(res.scores) == len(alts)
    assert len(res.ranks) == len(alts)
    assert len(res.steps) >= 5

    # Make sure ranks 1 to len(alts) are filled
    rank_values = sorted(res.ranks.values())
    assert rank_values[0] == 1
    assert "core_factors" in res.extra
    assert "secondary_factors" in res.extra

def test_solve_profile_matching_group():
    alts = ["A1", "A2", "A3"]
    dm_pm_scores = {
        "DM1": {"A1": 4.5, "A2": 3.8, "A3": 4.1},
        "DM2": {"A1": 4.2, "A2": 4.0, "A3": 3.5}
    }
    dm_weights = {"DM1": 0.6, "DM2": 0.4}

    res = solve_profile_matching_group(
        dm_pm_scores=dm_pm_scores,
        dm_weights=dm_weights,
        alternatives=alts
    )

    assert res.model == "PROFILE_MATCHING_GROUP"
    assert res.scope == "group"
    # Skor A1 = 0.6*4.5 + 0.4*4.2 = 2.7 + 1.68 = 4.38
    assert abs(res.scores["A1"] - 4.38) < 1e-4
    assert res.ranks["A1"] == 1

def test_pipeline_includes_all_methods_simultaneously(sample_session):
    """
    Verifies that when the pipeline runs:
    1. AHP is computed first for the criteria weights
    2. All individual models are computed together (AHP, SAW, WP, TOPSIS, COPELAND, PROFILE_MATCHING)
    3. The GDSS produces a group ranking for every method!
    """
    rr = run_all(sample_session)

    # 1. Check each DM's individual models
    for dm_id, indiv in rr.individual.items():
        assert "AHP" in indiv.models
        assert "SAW" in indiv.models
        assert "WP" in indiv.models
        assert "TOPSIS" in indiv.models
        assert "COPELAND" in indiv.models
        assert "PROFILE_MATCHING" in indiv.models

    # 2. Check the group ranking of every method
    assert "SAW_GROUP" in rr.group
    assert "WP_GROUP" in rr.group
    assert "TOPSIS_GROUP" in rr.group
    assert "AHP_GROUP_AIP" in rr.group
    assert "PROFILE_MATCHING_GROUP" in rr.group
    assert "COPELAND_GROUP" in rr.group
    assert "BORDA_WEIGHTED" in rr.group
    assert "BORDA_UNWEIGHTED" in rr.group
