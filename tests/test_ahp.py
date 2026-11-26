import json
from pathlib import Path
import numpy as np
import pytest

from engine.ahp import calculate_ahp_weights, solve_ahp_individual
from engine.schemas import Session

def test_ahp_l1_motor():
    """L-1 AHP (Exercise 1, motorbike criteria matrix)"""
    pairwise = [
        [1, 2, 3, "1/2"],
        ["1/2", 1, 4, 3],
        ["1/3", "1/4", 1, "1/3"],
        [2, "1/3", 3, 1]
    ]
    labels = ["C1", "C2", "C3", "C4"]
    w, l_max, ci, cr, steps, suggestions = calculate_ahp_weights(pairwise, labels)
    
    expected_w = [0.299, 0.348, 0.079, 0.274]
    for calc, exp in zip(w, expected_w):
        assert abs(calc - exp) < 0.005
    
    assert abs(l_max - 4.566) < 0.005
    assert abs(ci - 0.189) < 0.005
    assert abs(cr - 0.210) < 0.005
    assert cr >= 0.1
    assert len(suggestions) > 0

def test_ahp_l2_asisten():
    """L-2 AHP (Exercise 2, assistant criteria)"""
    pairwise = [
        [1, 2, "1/2", 3],
        ["1/2", 1, "1/3", 2],
        [2, 3, 1, 4],
        ["1/3", "1/2", "1/4", 1]
    ]
    labels = ["C1", "C2", "C3", "C4"]
    w, l_max, ci, cr, steps, suggestions = calculate_ahp_weights(pairwise, labels)
    
    expected_w = [0.277, 0.161, 0.466, 0.096]
    for calc, exp in zip(w, expected_w):
        assert abs(calc - exp) < 0.005

def test_ahp_g3_dm_weights():
    """G-3 DM weights (Facilitator)"""
    pairwise = [
        [1, 2, 3, 3, 4],
        ["1/2", 1, 2, 2, 3],
        ["1/3", "1/2", 1, 1, 2],
        ["1/3", "1/2", 1, 1, 2],
        ["1/4", "1/3", "1/2", "1/2", 1]
    ]
    labels = ["DM1", "DM2", "DM3", "DM4", "DM5"]
    w, l_max, ci, cr, steps, suggestions = calculate_ahp_weights(pairwise, labels)

    expected_w = [0.4017, 0.2442, 0.1373, 0.1373, 0.0794]
    for calc, exp in zip(w, expected_w):
        assert abs(calc - exp) < 5e-4
    
    assert abs(l_max - 5.0331) < 5e-4
    assert abs(cr - 0.0074) < 5e-4

def test_ahp_g1_and_individual():
    """G-1 Criteria weights and AHP score per DM in sample_case.json"""
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

        model_res, w, l_max, ci, cr, sug = solve_ahp_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            pairwise_raw=dm_in.pairwise,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )

        # Check the criteria weights
        for c, weight in zip(dm_in.criteria, w):
            assert abs(weight - gold_dm["weights"][c]) < 5e-4
        
        # Check lambda_max and CR
        assert abs(l_max - gold_dm["lambda_max"]) < 5e-4
        assert abs(cr - gold_dm["CR"]) < 5e-4

        # Check the AHP score
        gold_ahp_scores = gold_dm["scores"]["AHP"]
        for i, a in enumerate(alt_ids):
            assert abs(model_res.scores[a] - gold_ahp_scores[i]) < 5e-4
            assert model_res.ranks[a] == gold_dm["ranks"]["AHP"][i]
