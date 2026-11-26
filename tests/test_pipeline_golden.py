import json
from pathlib import Path
import pytest

from engine.schemas import Session
from engine.pipeline import run_all

def test_full_pipeline_golden():
    """
    Checks the whole GDSS pipeline against data/expected/golden_results.json.
    Covers:
    - DM weights (G-3)
    - Criteria weights per DM (G-1)
    - Individual scores and ranks (G-2)
    - Borda unweighted (G-4)
    - Borda weighted (G-5)
    - Group Copeland (G-6)
    - Group AHP AIP (G-7)
    - TOPSIS boundaries (G-8)
    - Copeland ties (G-9)
    """
    data_path = Path(__file__).resolve().parent.parent / "data" / "sample_case.json"
    golden_path = Path(__file__).resolve().parent.parent / "data" / "expected" / "golden_results.json"

    with open(data_path, "r", encoding="utf-8") as f:
        session = Session.model_validate(json.load(f))
    with open(golden_path, "r", encoding="utf-8") as f:
        golden = json.load(f)

    result = run_all(session)
    alt_ids = [a.id for a in session.alternatives]

    # 1. Check the DM weights (G-3)
    for dm_id, expected_w in golden["dm_weights"]["weights"].items():
        calc_w = result.dm_weights.weights[dm_id]
        assert abs(calc_w - expected_w) < 5e-4, f"DM weight {dm_id}: {calc_w} != {expected_w}"
    assert abs(result.dm_weights.CR - golden["dm_weights"]["CR"]) < 5e-4

    # 2. Check the individual models per DM (G-1, G-2)
    for dm_id, gold_dm in golden["dm"].items():
        indiv = result.individual[dm_id]
        # Criteria weights
        for c, exp_w in gold_dm["weights"].items():
            assert abs(indiv.criteria_weights[c] - exp_w) < 5e-4
        assert abs(indiv.consistency["lambda_max"] - gold_dm["lambda_max"]) < 5e-4
        assert abs(indiv.consistency["CR"] - gold_dm["CR"]) < 5e-4

        # Model scores & ranks
        for m_name in ["AHP", "SAW", "TOPSIS", "COPELAND"]:
            m_res = indiv.models[m_name]
            gold_scores = gold_dm["scores"][m_name]
            gold_ranks = gold_dm["ranks"][m_name]

            for i, a in enumerate(alt_ids):
                assert abs(m_res.scores[a] - gold_scores[i]) < 5e-4, f"{dm_id} {m_name} {a}: {m_res.scores[a]} != {gold_scores[i]}"
                assert m_res.ranks[a] == gold_ranks[i], f"{dm_id} {m_name} {a} rank: {m_res.ranks[a]} != {gold_ranks[i]}"

    # 3. Check unweighted Borda (G-4)
    gold_bu = golden["group"]["BORDA_unweighted"]
    calc_bu = result.group["BORDA_UNWEIGHTED"]
    for i, a in enumerate(alt_ids):
        assert abs(calc_bu.scores[a] - gold_bu["scores"][i]) < 5e-4
        assert calc_bu.ranks[a] == gold_bu["ranks"][i]

    # 4. Check weighted Borda (G-5)
    gold_bw = golden["group"]["BORDA_weighted"]
    calc_bw = result.group["BORDA_WEIGHTED"]
    for i, a in enumerate(alt_ids):
        assert abs(calc_bw.scores[a] - gold_bw["scores"][i]) < 5e-4
        assert calc_bw.ranks[a] == gold_bw["ranks"][i]

    # 5. Check group Copeland (G-6)
    gold_cg = golden["group"]["COPELAND_group"]
    calc_cg = result.group["COPELAND_GROUP"]
    for i, a in enumerate(alt_ids):
        assert abs(calc_cg.scores[a] - gold_cg["points"][i]) < 5e-4
        assert calc_cg.ranks[a] == gold_cg["ranks"][i]
        assert calc_cg.extra["wins"][a] == gold_cg["win"][i]
        assert calc_cg.extra["losses"][a] == gold_cg["lose"][i]

    # 6. Check group AHP AIP (G-7)
    gold_aip = golden["group"]["AHP_group_AIP"]
    calc_aip = result.group["AHP_GROUP_AIP"]
    for i, a in enumerate(alt_ids):
        assert abs(calc_aip.scores[a] - gold_aip["scores"][i]) < 5e-4
        assert calc_aip.ranks[a] == gold_aip["ranks"][i]

    # 7. Check the winners
    assert result.winners["BORDA_WEIGHTED"] == ["A6"]
    assert result.winners["BORDA_UNWEIGHTED"] == ["A2"]
    assert result.winners["COPELAND_GROUP"] == ["A6"]
    assert result.winners["AHP_GROUP_AIP"] == ["A6"]
