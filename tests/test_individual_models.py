import json
from pathlib import Path
import numpy as np
import pytest

from engine.schemas import Session
from engine.ahp import solve_ahp_individual
from engine.saw import solve_saw_individual
from engine.wp import solve_wp_individual
from engine.topsis import solve_topsis_individual
from engine.copeland import solve_copeland_criteria

def test_copeland_l4_lecturer():
    """L-4 Criteria Copeland (5 employees, 7 criteria)"""
    alts = ["Ahmad", "Ihsan", "Akbar", "Asrul", "Anwar"]
    crits = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    crit_types = {c: "benefit" for c in crits}
    # weights 23/20/18/15/11/8/5 %
    w = np.array([0.23, 0.20, 0.18, 0.15, 0.11, 0.08, 0.05])
    
    # Data L-4:
    raw_table = {
        "Ahmad": [113.67, 91.25, 91.58, 94.65, 92.25, 91.33, 91.98],
        "Ihsan": [107.14, 93.13, 92.85, 96.15, 92.80, 93.73, 94.69],
        "Akbar": [106.02, 94.98, 94.87, 95.90, 94.65, 94.45, 94.65],
        "Asrul": [108.75, 94.55, 91.22, 92.45, 91.55, 93.63, 92.16],
        "Anwar": [110.15, 96.48, 92.55, 94.10, 95.39, 93.82, 94.10]
    }
    values = {a: {c: raw_table[a][j] for j, c in enumerate(crits)} for a in alts}

    res = solve_copeland_criteria(
        dm_id="Dosen",
        criteria=crits,
        criteria_weights=w,
        alternatives=alts,
        criteria_types=crit_types,
        values=values
    )

    # points −2, 0, 2, −4, 4; ranks 4, 3, 2, 5, 1
    expected_points = {"Ahmad": -2.0, "Ihsan": 0.0, "Akbar": 2.0, "Asrul": -4.0, "Anwar": 4.0}
    expected_ranks = {"Ahmad": 4, "Ihsan": 3, "Akbar": 2, "Asrul": 5, "Anwar": 1}

    for a in alts:
        assert res.scores[a] == expected_points[a]
        assert res.ranks[a] == expected_ranks[a]

def test_golden_individual_models():
    """G-2, G-8, G-9 pengujian model individu terhadap golden_results.json"""
    data_path = Path(__file__).resolve().parent.parent / "data" / "sample_case.json"
    golden_path = Path(__file__).resolve().parent.parent / "data" / "expected" / "golden_results.json"
    
    with open(data_path, "r", encoding="utf-8") as f:
        session = Session.model_validate(json.load(f))
    with open(golden_path, "r", encoding="utf-8") as f:
        golden = json.load(f)

    crit_types = {c.id: c.type for c in session.criteria}
    alt_ids = [a.id for a in session.alternatives]

    for dm_id in ["DM1", "DM2", "DM3", "DM4", "DM5"]:
        dm_in = session.dm_inputs[dm_id]
        gold_dm = golden["dm"][dm_id]

        ahp_res, w, l_max, ci, cr, sug = solve_ahp_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            pairwise_raw=dm_in.pairwise,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )

        saw_res = solve_saw_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            criteria_weights=w,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )

        topsis_res = solve_topsis_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            criteria_weights=w,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )

        copeland_res = solve_copeland_criteria(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            criteria_weights=w,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )

        wp_res = solve_wp_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            criteria_weights=w,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )

        # Check SAW
        for i, a in enumerate(alt_ids):
            assert abs(saw_res.scores[a] - gold_dm["scores"]["SAW"][i]) < 5e-4
            assert saw_res.ranks[a] == gold_dm["ranks"]["SAW"][i]

        # Check TOPSIS
        for i, a in enumerate(alt_ids):
            assert abs(topsis_res.scores[a] - gold_dm["scores"]["TOPSIS"][i]) < 5e-4
            assert topsis_res.ranks[a] == gold_dm["ranks"]["TOPSIS"][i]

        # Check Copeland
        for i, a in enumerate(alt_ids):
            assert abs(copeland_res.scores[a] - gold_dm["scores"]["COPELAND"][i]) < 5e-4
            assert copeland_res.ranks[a] == gold_dm["ranks"]["COPELAND"][i]

        # Check that WP runs normally and its ranking is valid
        assert len(wp_res.scores) == 7
        assert len(wp_res.ranks) == 7
        assert abs(sum(wp_res.scores.values()) - 1.0) < 1e-4

        # G-8: DM5 TOPSIS A1=1.0000, A6=0.0000
        if dm_id == "DM5":
            assert abs(topsis_res.scores["A1"] - 1.0) < 5e-4
            assert abs(topsis_res.scores["A6"] - 0.0) < 5e-4

        # G-9: DM2 Copeland tie at rank 4 for A1, A3, A4
        if dm_id == "DM2":
            assert copeland_res.ranks["A1"] == 4
            assert copeland_res.ranks["A3"] == 4
            assert copeland_res.ranks["A4"] == 4
