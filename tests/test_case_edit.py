"""Pure tests (no UI) for case structure editing: add/remove, synchronisation, validation and running in the engine."""
import json
import random
from pathlib import Path

import pytest

from app import case_edit as ce
from app.state import load_sample_session
from engine.pipeline import run_all
from engine.schemas import Session

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def sample() -> Session:
    return load_sample_session()


def _fill(s: Session, seed: int = 1) -> Session:
    """Fill every value with a random positive number so the case can be analysed."""
    rnd = random.Random(seed)
    table = {a.id: {c.id: round(rnd.uniform(1, 100), 2) for c in s.criteria} for a in s.alternatives}
    return ce.apply_value_table(s, table)


# ── Synchronisation and add/remove ────────────────────────────────────────────
def test_sample_has_all_criteria_for_every_dm_and_ahp(sample):
    crit = [c.id for c in sample.criteria]
    assert len(crit) == 7 and len(sample.dms) == 5
    for dm in sample.dms:
        inp = sample.dm_inputs[dm.id]
        assert inp.criteria == crit and inp.chosen_method == "AHP"
        assert len(inp.pairwise) == 7


def test_add_criterion_keeps_old_judgements_and_new_pairs_are_equal(sample):
    old = sample.dm_inputs["DM2"].pairwise
    s = ce.add_criterion(sample)
    assert [c.id for c in s.criteria][-1] == "C8"
    pw = s.dm_inputs["DM2"].pairwise
    assert len(pw) == 8 and pw[0][7] == 1 and pw[7][0] == 1
    assert pw[0][1] == old[0][1] and pw[2][5] == old[2][5]
    # values of the products on a new criterion start at 0
    assert all(s.values[a.id]["C8"] == 0.0 for a in s.alternatives)


def test_remove_criterion_drops_only_its_pairs(sample):
    old = sample.dm_inputs["DM1"].pairwise  # urutan C1..C7
    s = ce.remove_criterion(sample, "C3")
    crit = [c.id for c in s.criteria]
    assert crit == ["C1", "C2", "C4", "C5", "C6", "C7"]
    pw = s.dm_inputs["DM1"].pairwise
    assert pw[0][2] == old[0][3]  # C1 vs C4 tetap
    assert pw[3][5] == old[4][6]  # C5 vs C7 tetap
    assert all("C3" not in v for v in s.values.values())


def test_reciprocal_cells_stay_consistent(sample):
    s = ce.add_dm(ce.add_alternative(ce.remove_criterion(sample, "C2")))
    for dm in s.dms:
        pw = s.dm_inputs[dm.id].pairwise
        n = len(pw)
        for i in range(n):
            assert pw[i][i] == 1
            for j in range(n):
                assert abs(ce.as_float(pw[i][j]) * ce.as_float(pw[j][i]) - 1) < 1e-9


def test_minimum_and_maximum_sizes_are_enforced(sample):
    s = sample
    for _ in range(20):
        s = ce.remove_alternative(s, s.alternatives[-1].id)
        s = ce.remove_criterion(s, s.criteria[-1].id)
        s = ce.remove_dm(s, s.dms[-1].id)
    assert (len(s.alternatives), len(s.criteria), len(s.dms)) == (ce.MIN_ALTERNATIVES, ce.MIN_CRITERIA, ce.MIN_DMS)
    for _ in range(30):
        s = ce.add_alternative(ce.add_criterion(ce.add_dm(s)))
    assert (len(s.alternatives), len(s.criteria), len(s.dms)) == (ce.MAX_ALTERNATIVES, ce.MAX_CRITERIA, ce.MAX_DMS)


def test_ids_stay_unique_after_remove_and_add(sample):
    s = ce.remove_alternative(sample, "A2")
    s = ce.add_alternative(s)
    s = ce.add_alternative(s)
    ids = [a.id for a in s.alternatives]
    assert len(ids) == len(set(ids))
    names = [a.name for a in s.alternatives]
    assert len(names) == len(set(n.lower() for n in names))


def test_vote_weighting_follows_dm_changes(sample):
    old = sample.dm_weighting.pairwise
    s = ce.remove_dm(sample, "DM3")
    assert s.dm_weighting.order == ["DM1", "DM2", "DM4", "DM5"]
    assert len(s.dm_weighting.pairwise) == 4
    assert s.dm_weighting.pairwise[0][1] == old[0][1]
    assert s.dm_weighting.pairwise[0][2] == old[0][3]  # DM1 vs DM4
    s = ce.add_dm(s)
    assert s.dm_weighting.order[-1] == "DM6" and s.dm_weighting.pairwise[0][4] == 1


def test_old_subset_session_is_normalised_and_runs():
    old = Session.model_validate(json.load(open(ROOT / "data" / "sample_case.json", encoding="utf-8")))
    assert len(old.dm_inputs["DM5"].criteria) == 3  # old file: every DM picked a subset
    s = ce.sync_session(old)
    assert all(len(i.criteria) == 7 and i.chosen_method == "AHP" for i in s.dm_inputs.values())
    # the pair DM5 assessed before (C3 vs C6) is kept
    old_pair = old.dm_inputs["DM5"].pairwise[0][1]
    assert s.dm_inputs["DM5"].pairwise[2][5] == old_pair
    run_all(s)


# ── Validation ─────────────────────────────────────────────────────────────────
def test_valid_sample_has_no_blocking_problem(sample):
    assert ce.blocking_problems(sample) == []


def test_validation_catches_duplicates_empty_names_and_bad_values(sample):
    s = sample.model_copy(deep=True)
    s.alternatives[1].name = s.alternatives[0].name
    s.criteria[0].name = "  "
    s.dms[0].role = ""
    s.values["A1"]["C3"] = 0  # C3 = cost
    s.values["A2"]["C1"] = -5
    problems = " | ".join(ce.blocking_problems(s))
    assert "is used twice" in problems
    assert "Name of criterion C1 is still empty" in problems
    assert "Name of role DM1 is still empty" in problems
    assert "(Cost) cannot be 0" in problems
    assert "is negative" in problems


def test_validation_flags_all_zero_benefit_column_and_warns_single_zero(sample):
    s = sample.model_copy(deep=True)
    s.values["A1"]["C1"] = 0  # a single zero cell on a benefit criterion: warning only
    kinds = [k for k, _ in ce.validate_case(s)]
    assert "warn" in kinds and "bad" not in kinds
    for a in s.alternatives:
        s.values[a.id]["C1"] = 0
    assert any("All values" in t for t in ce.blocking_problems(s))


def test_validation_minimums():
    s = ce.blank_session()
    s = s.model_copy(update={"alternatives": s.alternatives[:2]})
    assert any("At least 3 candidate products" in t for t in ce.blocking_problems(s))


def test_blank_session_is_blocked_until_filled():
    s = ce.blank_session()
    assert ce.blocking_problems(s)  # all values are 0
    filled = _fill(s)
    assert ce.blocking_problems(filled) == []
    res = run_all(filled)
    assert len(res.alternatives) == 3 and abs(sum(res.dm_weights.weights.values()) - 1) < 1e-9


def test_apply_value_table_ignores_garbage(sample):
    s = ce.apply_value_table(sample, {"A1": {"C1": "abc", "C2": None, "C3": float("nan"), "C4": "12.5"}})
    assert s.values["A1"]["C1"] == sample.values["A1"]["C1"]
    assert s.values["A1"]["C2"] == sample.values["A1"]["C2"]
    assert s.values["A1"]["C3"] == sample.values["A1"]["C3"]
    assert s.values["A1"]["C4"] == 12.5


# ── Engine with various sizes ────────────────────────────────────────────
@pytest.mark.parametrize("na,nc,nd", [(3, 3, 2), (4, 3, 3), (12, 10, 10), (5, 10, 2), (12, 3, 10)])
def test_engine_runs_for_many_sizes(na, nc, nd):
    s = ce.blank_session()
    while len(s.alternatives) < na:
        s = ce.add_alternative(s)
    while len(s.criteria) < nc:
        s = ce.add_criterion(s)
    while len(s.dms) < nd:
        s = ce.add_dm(s)
    # mix of benefit and cost
    s = s.model_copy(update={"criteria": [c.model_copy(update={"type": "cost" if i % 2 else "benefit"}) for i, c in enumerate(s.criteria)]})
    s = _fill(s, seed=na * 100 + nc)
    s = s.model_copy(update={"dm_weighting": s.dm_weighting.model_copy(update={"mode": "ahp"})})
    assert ce.blocking_problems(s) == []
    res = run_all(s)
    assert len(res.alternatives) == na and len(res.individual) == nd
    assert abs(sum(res.dm_weights.weights.values()) - 1) < 1e-9
    for g in res.group.values():
        assert set(g.ranks) == set(res.alternatives) and min(g.ranks.values()) == 1
