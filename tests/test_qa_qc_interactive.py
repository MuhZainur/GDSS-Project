import json
from pathlib import Path
import pytest
import numpy as np

from engine.schemas import Session
from engine.pipeline import run_all
from engine.sensitivity import simulate_what_if
from app.components.charts import (
    chart_bar_scores,
    chart_rank_heatmap,
    chart_bump,
    chart_stacked_contributions,
    chart_stacked_borda_contributions,
    chart_topsis_scatter,
    chart_copeland_matrix,
    chart_weights_bar,
    chart_dm_weights,
    chart_agreement_heatmap
)
from app.components.step_renderer import render_step
from app.components.pairwise_slider import render_pairwise_slider
from llm.payload import build_llm_payload

@pytest.fixture
def sample_session():
    data_path = Path(__file__).resolve().parent.parent / "data" / "sample_case.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return Session.model_validate(json.load(f))

@pytest.fixture
def run_result(sample_session):
    return run_all(sample_session)

def test_qa_all_charts_render(run_result, sample_session):
    """QA/QC: Memverifikasi seluruh 10 fungsi grafik Plotly menghasilkan Figure valid tanpa error."""
    alt_names = run_result.alternative_names
    crit_names = {c.id: c.name for c in sample_session.criteria}

    # 1. Bar scores
    for g_key, g_res in run_result.group.items():
        fig = chart_bar_scores(g_res.scores, alt_names, title=g_key)
        assert fig is not None
        assert len(fig.data) > 0

    # 2. Heatmap
    fig_hm = chart_rank_heatmap(run_result, alt_names)
    assert fig_hm is not None
    assert len(fig_hm.data) > 0

    # 3. Bump chart
    fig_bump = chart_bump(run_result, alt_names)
    assert fig_bump is not None
    assert len(fig_bump.data) == len(run_result.alternatives)

    # 4. Stacked contributions (AHP and SAW for all DMs)
    for dm_id in run_result.individual.keys():
        for m_name in ["AHP", "SAW"]:
            fig_sc = chart_stacked_contributions(run_result, dm_id, m_name, alt_names, crit_names)
            assert fig_sc is not None, f"The contribution chart of {m_name} for {dm_id} could not be built"
            assert len(fig_sc.data) > 0

    # 5. Stacked Borda DM contributions
    fig_borda = chart_stacked_borda_contributions(run_result, alt_names)
    assert fig_borda is not None
    assert len(fig_borda.data) == len(run_result.individual)

    # 6. TOPSIS scatter
    for dm_id in run_result.individual.keys():
        fig_ts = chart_topsis_scatter(run_result, dm_id, alt_names)
        assert fig_ts is not None
        assert len(fig_ts.data) > 0

    # 7. Copeland matrix (group and individual)
    fig_cg = chart_copeland_matrix(run_result, alt_names, model_key="COPELAND_GROUP")
    assert fig_cg is not None

    for dm_id in run_result.individual.keys():
        fig_ci = chart_copeland_matrix(run_result, alt_names, dm_id=dm_id)
        assert fig_ci is not None

    # 8. Weights bar & DM weights
    fig_wb = chart_weights_bar(run_result, alt_names, crit_names)
    assert fig_wb is not None
    fig_dmw = chart_dm_weights(run_result)
    assert fig_dmw is not None

    # 9. Agreement heatmap
    fig_agree = chart_agreement_heatmap(run_result)
    assert fig_agree is not None

def test_qa_what_if_sensitivity(run_result):
    """QA/QC: tests the what-if simulation with various weight configurations."""
    # Skenario 1: CEO mutlak (1.0, 0, 0, 0, 0)
    w_ceo = {"DM1": 1.0, "DM2": 0.0, "DM3": 0.0, "DM4": 0.0, "DM5": 0.0}
    sim1 = simulate_what_if(run_result, w_ceo)
    assert sim1["winners"]["BORDA_WEIGHTED"] == ["A6"] # DM1 chosen is AHP, ranking 1 is A6

    # Scenario 2: the CMO decides alone (DM3, chosen SAW, winner A2)
    w_cmo = {"DM1": 0.0, "DM2": 0.0, "DM3": 1.0, "DM4": 0.0, "DM5": 0.0}
    sim2 = simulate_what_if(run_result, w_cmo)
    assert sim2["winners"]["BORDA_WEIGHTED"] == ["A2"]

    # Scenario 3: balanced weights
    w_equal = {d: 0.2 for d in run_result.individual.keys()}
    sim3 = simulate_what_if(run_result, w_equal)
    assert len(sim3["winners"]) == 3

def test_qa_step_renderer_integrity(run_result):
    """QA/QC: verifies that every step of every model has a valid structure."""
    # Check the individual models
    for dm_id, indiv in run_result.individual.items():
        for m_name, m_res in indiv.models.items():
            assert len(m_res.steps) > 0, f"Model {m_name} of {dm_id} has no steps"
            for s in m_res.steps:
                assert s.id is not None
                assert s.title is not None
                if s.table:
                    assert len(s.table.columns) > 0
                    assert len(s.table.rows) > 0
                    # Make sure the number of columns equals the header
                    for row in s.table.rows:
                        assert len(row) == len(s.table.columns), f"Row size does not match in {s.id}"

    # Check the group models
    for g_name, g_res in run_result.group.items():
        assert len(g_res.steps) > 0, f"Model {g_name} has no steps"
        for s in g_res.steps:
            assert s.id is not None
            assert s.title is not None
            if s.table:
                for row in s.table.rows:
                    assert len(row) == len(s.table.columns), f"Row size does not match in {s.id}"

def test_qa_llm_payload_integrity(sample_session, run_result):
    """QA/QC: verifies that the payload sent to the LLM is valid and complete."""
    payload = build_llm_payload(sample_session, run_result)
    assert payload["run_id"] == run_result.run_id
    assert len(payload["alternatives"]) == 7
    assert len(payload["criteria"]) == 7
    assert len(payload["dm"]) == 5
    assert "flags" in payload
    assert "ties" in payload["flags"]
    assert "close_calls" in payload["flags"]
    assert "method_notes" in payload
    # Make sure WP is included in method_notes
    assert "WP" in payload["method_notes"]
