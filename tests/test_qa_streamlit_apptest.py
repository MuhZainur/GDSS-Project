"""
QA/QC of the "Decision Room" interface with Streamlit AppTest.
Focus: no exception on any page, no leaking or stuck state, displayed numbers = engine numbers.
Storage is redirected to a temporary folder so the real storage/ is never touched.
"""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import app.repository as repo
from app.insights import agreement_matrix, consensus
from app.labels import METHOD_ORDER
from app.state import PAGES
from engine.pipeline import run_all
from engine.schemas import Session

ROOT = Path(__file__).resolve().parent.parent
APP_FILE = str(ROOT / "app" / "main.py")


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    monkeypatch.setattr(repo, "STORAGE_DIR", storage)
    monkeypatch.setattr(repo, "SESSIONS_DIR", storage / "sessions")
    monkeypatch.setattr(repo, "RUNS_DIR", storage / "runs")
    monkeypatch.setattr(repo, "CHATS_DIR", storage / "chats")
    # Keys from the developer's .env must not make the tests depend on this machine.
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODELS", raising=False)
    # main.py calls load_dotenv() on every run; without this the real keys from .env would leak into the tests.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)


@pytest.fixture
def sample_session() -> Session:
    from app.state import load_sample_session

    return load_sample_session()


def fresh() -> AppTest:
    at = AppTest.from_file(APP_FILE, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def analyzed() -> AppTest:
    at = fresh()
    at.button(key="mast_run").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def goto(at: AppTest, page: str) -> AppTest:
    at.radio(key="nav_page").set_value(page).run()
    assert not at.exception, f"{page}: {[e.value for e in at.exception]}"
    return at


def md_text(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


# ── Basic flow ───────────────────────────────────────────────────────────────
def test_initial_render_and_all_pages_before_run():
    at = fresh()
    assert at.session_state.run_result is None
    for page in PAGES:
        goto(at, page)


def test_run_from_masthead_sets_result_and_goes_to_summary():
    at = analyzed()
    assert at.session_state.run_result is not None
    assert at.session_state.nav_page == "Summary"
    assert "NX-Train 200" in md_text(at), "The recommendation must show on the Summary"
    assert "Analysis up to date" in md_text(at)


def test_summary_matches_engine_consensus(sample_session):
    at = analyzed()
    cons = consensus(run_all(sample_session))
    best_name = {a.id: a.name for a in sample_session.alternatives}[cons["best"]]
    assert best_name in md_text(at)
    assert f"{len(cons['agree'])} of {cons['n_methods']}" in md_text(at)


def test_all_pages_after_run():
    at = analyzed()
    for page in PAGES:
        goto(at, page)


# ── Results by method: every method x point of view combination ─────────────────
def test_every_method_and_perspective_renders():
    at = analyzed()
    goto(at, "Results by method")
    dm_ids = list(at.session_state.run_result.individual.keys())
    for method in METHOD_ORDER:
        at.radio(key="nav_method").set_value(method).run()
        assert not at.exception, f"{method}: {[e.value for e in at.exception]}"
        if method == "BORDA":
            continue  # Borda only has a group view
        for persp in ["Group"] + dm_ids:
            at.radio(key="pill_perspective").set_value(persp).run()
            assert not at.exception, f"{method}/{persp}: {[e.value for e in at.exception]}"


def test_wp_s_vector_matches_engine_step(sample_session):
    """The 'S vector' column in the UI is derived from V x sum_S; it must equal the engine's step table."""
    res = run_all(sample_session).individual["DM1"].models["WP"]
    step = next(s for s in res.steps if s.id.endswith("vector_s"))
    engine_s = {row[0]: float(row[-1]) for row in step.table.rows}
    for a, v in res.scores.items():
        assert v * res.meta["sum_S"] == pytest.approx(engine_s[a], abs=1e-4)


# ── Team assessment ────────────────────────────────────────────────────────────
def test_pairwise_slider_updates_session_and_flags_stale():
    at = analyzed()
    goto(at, "Team assessment")
    at.select_slider(key="pw_DM1_C1_C4").set_value(-2).run()  # C1 is more important than C4, scale 3
    assert not at.exception
    inp = at.session_state.session.dm_inputs["DM1"]
    assert inp.criteria == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"], "Every criterion must be assessed"
    assert inp.pairwise[0][3] == 3 and inp.pairwise[3][0] == "1/3"
    goto(at, "Summary")
    assert "Data changed" in md_text(at)
    at.button(key="mast_run").click().run()
    assert not at.exception
    assert "Analysis up to date" in md_text(at)


def test_assessment_has_no_criteria_picker_and_no_reference_method():
    at = fresh()
    goto(at, "Team assessment")
    keys = {w.key for w in at.multiselect} | {w.key for w in at.radio}
    assert not any(str(k).startswith("dm_crits_") or str(k).startswith("dm_method_") for k in keys)
    assert "Reference method" not in md_text(at)
    # 7 criteria -> 21 sliders per DM
    assert len([s for s in at.select_slider if s.key.startswith("pw_DM1_")]) == 21


def test_all_dms_use_ahp_as_reference(sample_session):
    assert {i.chosen_method for i in sample_session.dm_inputs.values()} == {"AHP"}
    at = analyzed()
    assert {v.chosen_method for v in at.session_state.run_result.individual.values()} == {"AHP"}


def test_visiting_assessment_page_does_not_mark_results_stale():
    at = analyzed()
    goto(at, "Team assessment")
    for dm in ["DM2", "DM3", "DM4", "DM5"]:
        at.radio(key="pill_dm_sel").set_value(dm).run()
        assert not at.exception
    goto(at, "Summary")
    assert "Analysis up to date" in md_text(at), "Merely opening the page must not change the data"


def test_vote_weight_mode_equal_then_ahp():
    at = analyzed()
    goto(at, "Team assessment")
    at.radio(key="pill_dmw_mode").set_value("Equal").run()
    assert not at.exception
    assert at.session_state.session.dm_weighting.mode == "equal"
    at.button(key="mast_run").click().run()
    w = at.session_state.run_result.dm_weights.weights
    assert all(abs(v - 0.2) < 1e-9 for v in w.values())
    goto(at, "Team assessment")
    at.radio(key="pill_dmw_mode").set_value("Assessed with AHP").run()
    at.select_slider(key="pw_dmw_DM1_DM2").set_value(-4).run()  # DM1 is 5x more influential than DM2
    assert not at.exception
    dw = at.session_state.session.dm_weighting
    assert dw.mode == "ahp" and dw.pairwise[0][1] == 5 and dw.pairwise[1][0] == "1/5"
    at.button(key="mast_run").click().run()
    w = at.session_state.run_result.dm_weights.weights
    assert w["DM1"] > w["DM2"] and abs(sum(w.values()) - 1) < 1e-9


# ── Case data: products, criteria and DMs can be edited ─────────────────────────────
def test_case_data_shows_editors_with_benefit_cost_dropdown():
    at = fresh()
    goto(at, "Case data")
    sel = at.selectbox(key="ed_crit_type_C3")
    assert list(sel.options) == ["Benefit", "Cost"]
    assert sel.value == "Cost"
    assert at.selectbox(key="ed_crit_type_C1").value == "Benefit"
    assert "Benefit / Cost" in md_text(at)


def test_rename_product_criterion_and_dm_propagates_to_results():
    at = fresh()
    goto(at, "Case data")
    at.text_input(key="ed_alt_name_A6").set_value("Flagship Product X").run()
    at.text_input(key="ed_crit_name_C1").set_value("Service Speed").run()
    at.text_input(key="ed_dm_role_DM1").set_value("Product Manager").run()
    assert not at.exception
    s = at.session_state.session
    assert s.alternatives[5].name == "Flagship Product X"
    assert s.criteria[0].name == "Service Speed" and s.dms[0].role == "Product Manager"
    at.button(key="mast_run").click().run()
    assert not at.exception
    assert "Flagship Product X" in md_text(at)
    goto(at, "Team assessment")
    assert "Product Manager" in list(at.radio(key="pill_dm_sel").options) or "DM1" in list(at.radio(key="pill_dm_sel").options)
    for page in PAGES:
        goto(at, page)


def test_change_criterion_type_changes_results_direction():
    at = analyzed()
    before = dict(at.session_state.run_result.group["SAW_GROUP"].scores)
    goto(at, "Case data")
    at.selectbox(key="ed_crit_type_C3").set_value("Benefit").run()  # cost now counts as higher is better
    assert at.session_state.session.criteria[2].type == "benefit"
    at.button(key="mast_run").click().run()
    assert not at.exception
    assert dict(at.session_state.run_result.group["SAW_GROUP"].scores) != before


def test_add_product_requires_values_before_analysis():
    at = fresh()
    goto(at, "Case data")
    at.button(key="ed_alt_add").click().run()
    assert not at.exception
    s = at.session_state.session
    assert len(s.alternatives) == 8 and s.alternatives[-1].id == "A8"
    assert "The data cannot be analysed yet" in md_text(at)  # Cost value = 0
    at.button(key="mast_run").click().run()
    assert at.session_state.run_result is None
    assert at.session_state.nav_page == "Case data"
    assert "The data cannot be analysed yet" in md_text(at)


def test_add_and_remove_criterion_updates_team_assessment():
    at = fresh()
    goto(at, "Case data")
    at.button(key="ed_crit_add").click().run()
    assert not at.exception
    s = at.session_state.session
    assert [c.id for c in s.criteria][-1] == "C8"
    assert all(len(i.criteria) == 8 for i in s.dm_inputs.values())
    goto(at, "Team assessment")
    assert len([x for x in at.select_slider if x.key.startswith("pw_DM1_")]) == 28
    goto(at, "Case data")
    at.button(key="ed_crit_del_C8").click().run()
    at.button(key="ed_crit_del_C7").click().run()
    s = at.session_state.session
    assert [c.id for c in s.criteria] == ["C1", "C2", "C3", "C4", "C5", "C6"]
    goto(at, "Team assessment")
    assert len([x for x in at.select_slider if x.key.startswith("pw_DM1_")]) == 15
    at.button(key="mast_run").click().run()
    assert not at.exception and at.session_state.run_result is not None


def test_add_and_remove_dm_keeps_everything_consistent():
    at = fresh()
    goto(at, "Case data")
    at.button(key="ed_dm_add").click().run()
    at.text_input(key="ed_dm_role_DM6").set_value("Branch Head").run()
    assert not at.exception
    s = at.session_state.session
    assert [d.id for d in s.dms][-1] == "DM6" and s.dm_weighting.order[-1] == "DM6" and "DM6" in s.dm_inputs
    at.button(key="ed_dm_del_DM2").click().run()
    s = at.session_state.session
    assert [d.id for d in s.dms] == ["DM1", "DM3", "DM4", "DM5", "DM6"] and "DM2" not in s.dm_inputs
    at.button(key="mast_run").click().run()
    assert not at.exception
    res = at.session_state.run_result
    assert set(res.individual) == {"DM1", "DM3", "DM4", "DM5", "DM6"}
    assert abs(sum(res.dm_weights.weights.values()) - 1) < 1e-9
    for page in PAGES:
        goto(at, page)


def test_delete_buttons_disabled_at_minimum():
    at = fresh()
    goto(at, "Case data")
    for aid in ["A7", "A6", "A5", "A4"]:
        at.button(key=f"ed_alt_del_{aid}").click().run()
    assert len(at.session_state.session.alternatives) == 3
    assert all(at.button(key=f"ed_alt_del_{a}").disabled for a in ["A1", "A2", "A3"])
    assert not at.exception


def test_shrink_to_minimum_then_everything_still_renders():
    at = fresh()
    goto(at, "Case data")
    for aid in ["A7", "A6", "A5", "A4"]:
        at.button(key=f"ed_alt_del_{aid}").click().run()
    for cid in ["C7", "C6", "C5", "C4"]:
        at.button(key=f"ed_crit_del_{cid}").click().run()
    for did in ["DM5", "DM4", "DM3"]:
        at.button(key=f"ed_dm_del_{did}").click().run()
    s = at.session_state.session
    assert (len(s.alternatives), len(s.criteria), len(s.dms)) == (3, 3, 2)
    at.button(key="mast_run").click().run()
    assert not at.exception and at.session_state.run_result is not None
    for page in PAGES:
        goto(at, page)
    goto(at, "Results by method")
    dm_ids = list(at.session_state.run_result.individual)
    for method in METHOD_ORDER:
        at.radio(key="nav_method").set_value(method).run()
        assert not at.exception, method
        if method == "BORDA":
            continue
        for persp in ["Group"] + dm_ids:
            at.radio(key="pill_perspective").set_value(persp).run()
            assert not at.exception, f"{method}/{persp}"


def test_blank_case_flow():
    from app import case_edit as ce

    at = fresh()
    at.button(key="side_new").click().run()
    assert not at.exception
    s = at.session_state.session
    assert (len(s.alternatives), len(s.criteria), len(s.dms)) == (3, 3, 2)
    assert at.session_state.nav_page == "Case data"
    at.button(key="mast_run").click().run()
    assert at.session_state.run_result is None and "The data cannot be analysed yet" in md_text(at)
    # Fill the values through the same function as the table editor; then the analysis must run
    table = {a.id: {c.id: float(i + j + 1) for j, c in enumerate(s.criteria)} for i, a in enumerate(s.alternatives)}
    at.session_state.session = ce.apply_value_table(s, table)
    at.run()
    at.button(key="mast_run").click().run()
    assert not at.exception and at.session_state.run_result is not None
    for page in PAGES:
        goto(at, page)


# ── Sessions and data ────────────────────────────────────────────────────────────
def test_reset_to_sample_restores_data_and_clears_widget_state():
    at = analyzed()
    goto(at, "Case data")
    at.text_input(key="ed_alt_name_A1").set_value("Temporary name").run()
    at.button(key="ed_dm_add").click().run()
    assert len(at.session_state.session.dms) == 6
    at.button(key="side_reset").click().run()
    assert not at.exception
    assert at.session_state.run_result is None
    s = at.session_state.session
    assert s.alternatives[0].name == "NX-Edge 10" and len(s.dms) == 5
    goto(at, "Case data")
    assert at.text_input(key="ed_alt_name_A1").value == "NX-Edge 10", "Old widget state must not stay stuck"


def test_save_and_load_session_roundtrip():
    at = fresh()
    at.button(key="side_sess_save").click().run()
    assert not at.exception
    assert repo.list_sessions() == [at.session_state.session.session_id]
    at.run()
    at.button(key="side_sess_load").click().run()
    assert not at.exception
    assert "loaded" in md_text(at)


def test_history_run_can_be_loaded_and_shows_in_status():
    at = analyzed()
    run_id = at.session_state.run_result.run_id
    assert run_id in repo.list_runs()
    at.run()
    at.button(key="side_run_load").click().run()
    assert not at.exception
    assert at.session_state.run_source == "history"
    assert run_id in md_text(at)


def test_broken_history_run_shows_error_not_crash():
    bad = repo.RUNS_DIR / "run-broken"
    bad.mkdir(parents=True)
    (bad / "results.json").write_text('{"run_id": "x"}', encoding="utf-8")
    at = fresh()
    assert "run-broken" in at.session_state.run_history
    at.selectbox(key="side_run_pick").set_value("run-broken").run()
    at.button(key="side_run_load").click().run()
    assert not at.exception
    assert "could not be read" in md_text(at)
    assert at.session_state.run_result is None


# ── Compare ─────────────────────────────────────────────────────────────
def test_whatif_extreme_weights_and_reset():
    from engine.sensitivity import simulate_what_if

    at = analyzed()
    result = at.session_state.run_result
    goto(at, "Compare")
    for dm in ["DM1", "DM2", "DM3", "DM4", "DM5"]:
        at.slider(key=f"wi_{dm}").set_value(0)
    at.slider(key="wi_DM3").set_value(100).run()  # all the votes to DM3
    assert not at.exception
    sim = simulate_what_if(result, {"DM1": 0, "DM2": 0, "DM3": 100, "DM4": 0, "DM5": 0})
    names = result.alternative_names
    for k in ["BORDA_WEIGHTED", "COPELAND_GROUP", "AHP_GROUP_AIP"]:
        for alt in sim["winners"][k]:
            assert names[alt] in md_text(at)
    changed = any(set(sim["winners"][k]) != {a for a, r in result.group[k].ranks.items() if r == 1}
                  for k in ["BORDA_WEIGHTED", "COPELAND_GROUP", "AHP_GROUP_AIP"])
    assert ("Changed" in md_text(at)) == changed
    at.button(key="wi_reset").click().run()
    assert not at.exception
    assert at.slider(key="wi_DM1").value == round(result.dm_weights.weights["DM1"] * 100)


def test_whatif_all_zero_weights_shows_warning_not_crash():
    at = analyzed()
    goto(at, "Compare")
    for dm in ["DM1", "DM2", "DM3", "DM4", "DM5"]:
        at.slider(key=f"wi_{dm}").set_value(0)
    at.run()
    assert not at.exception
    assert "above 0" in md_text(at)


def test_agreement_matrix_is_not_trivially_one(sample_session):
    """Regression: the old version read the 'A|B' format wrongly so every cell = 1.0."""
    result = run_all(sample_session)
    keys, mat = agreement_matrix(result)
    off_diag = [mat[i][j] for i in range(len(keys)) for j in range(len(keys)) if i != j]
    assert all(v is not None for v in off_diag)
    assert min(off_diag) < 0.95


# ── AI assistant ───────────────────────────────────────────────────────────────
def test_ai_page_without_key_asks_for_key_and_never_touches_environ():
    import os

    at = analyzed()
    goto(at, "AI assistant")
    assert "key missing" in md_text(at)
    at.text_input(key="ai_key_input_gemini").set_value("test-key-123").run()
    assert not at.exception
    assert "GOOGLE_API_KEY" not in os.environ, "The user key must never leak into the process environment"
    assert at.session_state.custom_gemini_key == "test-key-123"


def test_ai_report_and_chat_with_mocked_llm(monkeypatch):
    import app.pages_.assistant as assistant

    calls = {}

    def fake_analysis(payload, api_key=None, provider=None, model=None, keys=None):
        calls["analysis"] = (api_key, provider, model, keys)
        return {
            "success": True,
            "model_used": "mock-model",
            "sections": {
                "rekomendasi": {"alternative": "A6 (NX-Train 200)", "reasons": ["reason one"]},
                "ringkasan": "Test summary",
            },
            "unverified_numbers": ["9.99"],
            "markdown": "# Test document",
            "notes": ["Test note about the engine."],
        }

    def fake_chat(**kwargs):
        calls["chat"] = kwargs
        return "Test answer", [], "mock-model"

    monkeypatch.setattr(assistant, "run_analysis", fake_analysis)
    monkeypatch.setattr(assistant, "chat_step", fake_chat)

    at = analyzed()
    at.session_state.custom_gemini_key = "test-key"
    at.session_state.custom_api_key = "or-key"
    goto(at, "AI assistant")
    assert "ready" in md_text(at)

    at.button(key="ai_do_analyze").click().run()
    assert not at.exception
    assert calls["analysis"][0] == "test-key" and calls["analysis"][1] == "gemini"
    assert calls["analysis"][3] == {"gemini": "test-key", "openrouter": "or-key"}, "Both keys are passed so fallback can work"
    text = md_text(at)
    assert "A6 (NX-Train 200)" in text
    assert "9.99" in text, "Unverified numbers must be flagged"
    assert "Test note about the engine." in text, "Engine notes must be shown to the user"

    at.radio(key="pill_ai_mode").set_value("Ask the assistant").run()
    assert not at.exception
    assert any(b.label.startswith("Why ") for b in at.button), "Dynamic starter questions must show"
    at.chat_input[0].set_value("What are the risks?").run()
    assert not at.exception
    assert calls["chat"]["user_message"] == "What are the risks?"
    assert calls["chat"]["api_key"] == "test-key"
    assert calls["chat"]["keys"] == {"gemini": "test-key", "openrouter": "or-key"}


def test_ai_model_choices_are_hydrogen_plus_large_free_models():
    import app.pages_.assistant as assistant
    from llm.client import OPENROUTER_FREE_MODELS, is_allowed_openrouter_model

    gem = [(label, m) for label, (p, m) in assistant.AI_MODELS.items() if p == "gemini"]
    assert [m for _, m in gem] == ["gemini-4-hydrogen"] and "thinking low" in gem[0][0]
    chosen = []
    for label, (prov, model) in assistant.AI_MODELS.items():
        if prov == "openrouter" and model:
            assert is_allowed_openrouter_model(model), label
            chosen.append(model)
    assert chosen == [m.id for m in OPENROUTER_FREE_MODELS], "The dropdown must list exactly the allowed models"
    assert not any("gemma" in k.lower() or "inkling" in k.lower() for k in assistant.AI_MODELS)
    at = analyzed()
    goto(at, "AI assistant")
    opts = list(at.selectbox(key="ai_model").options)
    assert opts == list(assistant.AI_MODELS) and not any("2.5" in o for o in opts)


def test_ai_report_fills_all_five_tabs_even_for_sparse_model_output(monkeypatch):
    """The model returns almost nothing; the real run_analysis with a fake LLM must still fill all five tabs."""
    from llm import analyze

    def fake_call(messages, provider=None, model=None, **kw):
        return '{"ringkasan": "short"}', "mock-model"

    monkeypatch.setattr(analyze, "call_llm", fake_call)
    at = analyzed()
    at.session_state.custom_gemini_key = "test-key"
    goto(at, "AI assistant")
    at.button(key="ai_do_analyze").click().run()
    assert not at.exception
    text = md_text(at)
    assert "written automatically" in text, "The user must be told that some sections were filled automatically"
    keys = [k for k in at.session_state.filtered_state if str(k).startswith("analysis_")]
    assert len(keys) == 1
    data = at.session_state[keys[0]]
    assert data["success"] and set(data["completeness"]["fallback"])
    assert all(data["sections"].get(k) for k in ["ringkasan", "perbandingan", "kelebihan_kelemahan", "risiko", "konsistensi", "rekomendasi"])
    for tab_label in ["Summary", "Across methods", "Strengths and weaknesses", "Risks and consistency", "Full document"]:
        assert any(tb.label == tab_label for tb in at.tabs), tab_label
    assert "(not stated)" not in text and "not available" not in text


def test_ai_report_is_saved_and_reopened_without_a_request(monkeypatch):
    from llm import analyze

    n = {"calls": 0}

    def fake_call(messages, provider=None, model=None, **kw):
        n["calls"] += 1
        return '{"ringkasan": "short"}', "mock-model"

    monkeypatch.setattr(analyze, "call_llm", fake_call)
    at = analyzed()
    at.session_state.custom_gemini_key = "test-key"
    run_id = at.session_state.run_result.run_id
    goto(at, "AI assistant")
    at.button(key="ai_do_analyze").click().run()
    assert n["calls"] == 1
    assert repo.load_analysis(run_id, "gemini_gemini-4-hydrogen")["success"]

    # a brand-new browser session that loads the same run from history must reopen the saved report without a request
    at2 = fresh()
    at2.session_state.custom_gemini_key = "test-key"
    at2.selectbox(key="side_run_pick").set_value(run_id).run()
    at2.button(key="side_run_load").click().run()
    assert not at2.exception
    assert at2.session_state.run_result.run_id == run_id
    goto(at2, "AI assistant")
    assert n["calls"] == 1, "Opening the page must not use a request"
    assert any("no API request used" in c.value for c in at2.caption), "The saved report must be labelled as such"


def test_ai_failed_report_shows_error():
    import app.pages_.assistant as assistant

    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(assistant, "run_analysis", lambda *a, **k: {"success": False, "error": "1) Gemini: quota used up 2) Dots3: busy"})
        at = analyzed()
        at.session_state.custom_gemini_key = "k"
        goto(at, "AI assistant")
        at.button(key="ai_do_analyze").click().run()
        assert not at.exception
        text = md_text(at)
        assert "quota used up" in text and "The report could not be created" in text
    finally:
        mp.undo()


# ── Robustness ────────────────────────────────────────────────────────────────
def test_html_injection_in_names_is_escaped(sample_session):
    evil = sample_session.model_copy(deep=True)
    evil.alternatives[0].name = "<script>alert(1)</script>"
    evil.company = "<img src=x onerror=alert(1)>"
    at = AppTest.from_file(APP_FILE, default_timeout=60)
    at.session_state.session = evil
    at.run()
    assert not at.exception
    at.button(key="mast_run").click().run()
    for page in PAGES:
        goto(at, page)
        text = md_text(at)
        assert "<script>" not in text and "<img src=x" not in text, f"HTML is not escaped on page {page}"


def test_ranking_ties_do_not_crash_summary(sample_session):
    """Two DMs with identical assessments give similar ranks; the summary must keep working."""
    s = sample_session.model_copy(deep=True)
    s.dm_inputs["DM4"] = s.dm_inputs["DM3"].model_copy(deep=True)
    at = AppTest.from_file(APP_FILE, default_timeout=60)
    at.session_state.session = s
    at.run()
    at.button(key="mast_run").click().run()
    assert not at.exception
    goto(at, "Compare")
