import pytest
from engine.borda import solve_borda_unweighted

def test_borda_l3_lecturer():
    """L-3 Borda (7 DM, 3 kandidat)"""
    alts = ["A", "B", "C"]
    dm_rankings = {
        "DM1": {"A": 2, "B": 1, "C": 3},
        "DM2": {"A": 3, "B": 2, "C": 1},
        "DM3": {"A": 3, "B": 1, "C": 2},
        "DM4": {"A": 2, "B": 1, "C": 3},
        "DM5": {"A": 2, "B": 3, "C": 1},
        "DM6": {"A": 3, "B": 1, "C": 2},
        "DM7": {"A": 2, "B": 1, "C": 3}
    }

    res = solve_borda_unweighted(dm_rankings, alts)

    # Expected points A = 4, B = 11, C = 6, total 21, weights (0.19, 0.52, 0.29)
    assert res.scores["A"] == 4.0
    assert res.scores["B"] == 11.0
    assert res.scores["C"] == 6.0
    assert abs(res.normalized["A"] - 0.19) < 0.01
    assert abs(res.normalized["B"] - 0.52) < 0.01
    assert abs(res.normalized["C"] - 0.29) < 0.01
    assert res.ranks["B"] == 1
    assert res.ranks["C"] == 2
    assert res.ranks["A"] == 3
