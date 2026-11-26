"""Tests of the AI report completeness guarantee: any model must end up with all six sections filled."""
import json
from unittest.mock import patch

import pytest

from app import case_edit as ce
from app.state import load_sample_session
from engine.pipeline import run_all
from llm import analyze
from llm.analyze import generate_markdown_from_sections, run_analysis
from llm.completeness import (
    AUTO_NOTE,
    SECTION_KEYS,
    TEXT_KEYS,
    assess,
    complete_sections,
    consensus_from_payload,
    normalize_sections,
    table_row_count,
)
from llm.payload import build_llm_payload

HARDCODED = ["NX-Train", "NX-Game", "NusaCompute", "CEO", "CTO"]


@pytest.fixture(scope="module")
def payload():
    s = load_sample_session()
    return build_llm_payload(s, run_all(s))


def _custom_payload():
    """A completely different case: product, criterion and DM role names differ from the sample."""
    s = ce.blank_session()
    s = ce.add_alternative(s)
    s = s.model_copy(update={
        "company": None,
        "alternatives": [a.model_copy(update={"name": n}) for a, n in zip(s.alternatives, ["Arabica Coffee", "Robusta Coffee", "Liberica Coffee", "Excelsa Coffee"])],
        "dms": [d.model_copy(update={"role": r}) for d, r in zip(s.dms, ["Farm Manager", "Market Manager"])],
    })
    table = {a.id: {c.id: float(3 + i * 2 + j + (i * j) % 3) for j, c in enumerate(s.criteria)} for i, a in enumerate(s.alternatives)}
    s = ce.apply_value_table(s, table)
    return build_llm_payload(s, run_all(s))


def _complete_sections(payload):
    names = {a["id"]: f'{a["id"]} ({a["name"]})' for a in payload["alternatives"]}
    best, second = (names[a] for a in consensus_from_payload(payload)["order"][:2])
    keys = list(payload["group_rankings"])
    table = "| Model | Strengths on This Data | Weaknesses on This Data |\n|---|---|---|\n" + "\n".join(
        f"| {k} | Strength of method {k} on this data. | Weakness of method {k} on this data. |" for k in keys
    )
    return {
        "ringkasan": f"The consensus winner is {best} and the runner-up is {second}. " * 3,
        "perbandingan": "Borda and Copeland use ranks while AHP and SAW use scores; that is why their results can differ. " * 3,
        "kelebihan_kelemahan": table,
        "rekomendasi": {
            "alternative": best, "based_on_model": "Consensus of all methods",
            "reasons": ["First data-backed reason.", "Second data-backed reason.", "Third reason."],
            "backup_alternative": second, "backup_condition": "If the vote weights shift towards another party.",
        },
        "risiko": "- The thin gaps between ranks make the order very sensitive to small data changes. " * 3,
        "konsistensi": "Every decision maker has a CR below 0.1, so the assessments are consistent and can be trusted. " * 2,
    }


def _assert_all_present(sections, payload):
    for k in TEXT_KEYS:
        assert isinstance(sections[k], str) and sections[k].strip(), k
    assert table_row_count(sections["kelebihan_kelemahan"]) >= min(5, len(payload["group_rankings"]))
    rec = sections["rekomendasi"]
    assert rec["alternative"] and rec["backup_alternative"] and rec["alternative"] != rec["backup_alternative"]
    assert len(rec["reasons"]) >= 2 and len(rec["backup_condition"]) >= 15
    assert assess(sections, payload) == {}, "The final result must pass the completeness assessment"


# ── A complete model output is left untouched ────────────────────────────────
def test_complete_model_output_passes_untouched(payload):
    sec = _complete_sections(payload)
    out, rep = complete_sections(sec, payload)
    assert rep == {"weak": [], "fallback": []}
    assert out["ringkasan"] == sec["ringkasan"].strip()
    _assert_all_present(out, payload)


# ── Different shapes of model output ─────────────────────────────────────────
def test_empty_output_is_filled_from_data(payload):
    out, rep = complete_sections({}, payload)
    _assert_all_present(out, payload)
    assert set(rep["fallback"]) == set(SECTION_KEYS)
    assert AUTO_NOTE.strip() in out["ringkasan"]


def test_fallback_uses_only_data_names_and_no_hardcoded_products():
    p = _custom_payload()
    out, _ = complete_sections({}, p)
    _assert_all_present(out, p)
    blob = json.dumps(out, ensure_ascii=False)
    assert any(n in blob for n in ["Arabica Coffee", "Robusta Coffee", "Liberica Coffee", "Excelsa Coffee"])
    for bad in HARDCODED:
        assert bad not in blob, bad
    assert "Farm Manager" in blob or "Market Manager" in blob


def test_sample_fallback_names_come_from_sample_data(payload):
    out, _ = complete_sections({}, payload)
    names = {a["name"] for a in payload["alternatives"]}
    assert any(n in out["ringkasan"] for n in names)


def test_fallback_text_is_english(payload):
    out, _ = complete_sections({}, payload)
    blob = " ".join(out[k] for k in TEXT_KEYS).lower()
    for word in [" yang ", " dan ", " untuk ", " dengan ", "juara", "kelebihan", "kelemahan", "tidak "]:
        assert word not in blob, word


def test_sections_as_lists_and_dicts_are_normalised(payload):
    sec = _complete_sections(payload)
    sec["risiko"] = ["Risk one that is long enough to read " * 2, "Risk two that is long enough to read " * 2, "Risk three"]
    sec["konsistensi"] = {"DM1": "CR 0.05 is consistent and very good to use for the decision", "DM2": "CR 0.07 is consistent and good too for the decision"}
    sec["kelebihan_kelemahan"] = [
        {"model": k, "strengths": f"strengths {k}", "weaknesses": f"weaknesses {k}"} for k in payload["group_rankings"]
    ]
    sec["rekomendasi"]["reasons"] = "- reason one\n- reason two\n- reason three"
    out, _ = complete_sections(sec, payload)
    assert out["risiko"].startswith("- Risk one")
    assert out["kelebihan_kelemahan"].startswith("| Model |")
    assert out["rekomendasi"]["reasons"] == ["reason one", "reason two", "reason three"]
    assert isinstance(out["konsistensi"], str) and "DM1" in out["konsistensi"]


def test_short_table_is_replaced_by_data_based_table(payload):
    sec = _complete_sections(payload)
    sec["kelebihan_kelemahan"] = "| Model | Strengths | Weaknesses |\n|---|---|---|\n| SAW | fast | sensitive |"
    out, rep = complete_sections(sec, payload)
    assert rep["fallback"] == ["kelebihan_kelemahan"]
    _assert_all_present(out, payload)


def test_only_the_weak_sections_are_replaced(payload):
    full = _complete_sections(payload)
    broken = {k: v for k, v in full.items() if k not in ("risiko", "rekomendasi")}
    out, rep = complete_sections(broken, payload)
    assert set(rep["fallback"]) == {"risiko", "rekomendasi"}
    assert out["ringkasan"] == full["ringkasan"].strip()
    _assert_all_present(out, payload)


def test_unknown_or_duplicate_recommendation_gets_corrected(payload):
    sec = _complete_sections(payload)
    sec["rekomendasi"] = {"alternative": "Fictional Product Zzz", "backup_alternative": "Fictional Product Zzz", "reasons": ["a"]}
    out, _ = complete_sections(sec, payload)
    _assert_all_present(out, payload)
    assert "Zzz" not in json.dumps(out)


def test_recommendation_given_as_string_is_kept_if_valid(payload):
    sec = _complete_sections(payload)
    best_id = consensus_from_payload(payload)["order"][0]
    sec["rekomendasi"] = best_id
    out, _ = complete_sections(sec, payload)
    assert out["rekomendasi"]["alternative"].startswith(best_id)
    _assert_all_present(out, payload)


def test_fallback_text_has_no_invented_numbers(payload):
    """Every decimal number in the fallback text must be traceable to the payload (rule: never invent numbers)."""
    out, _ = complete_sections({}, payload)
    text = "\n".join(out[k] for k in TEXT_KEYS) + json.dumps(out["rekomendasi"], ensure_ascii=False)
    nums = analyze.extract_all_numbers_from_json(payload)
    unverified = analyze.validate_numbers_in_text(text, nums)
    # the average rank is a simple derivative of the ranks in the payload; everything else must match exactly
    cons = consensus_from_payload(payload)
    derived = {f"{v:.2f}" for v in cons["avg"].values()}
    assert [u for u in unverified if u not in derived] == []


# ── run_analysis with a fake LLM: model A complete, B truncated, C markdown, D empty ──
def _fake_llm(replies):
    calls = []

    def fake(messages, provider=None, model=None, temperature=0.2, max_tokens=0, api_key=None, json_mode=False,
             keys=None, attempts=None, **kw):
        calls.append({"messages": messages, "model": model, "max_tokens": max_tokens, "keys": keys})
        r = replies[min(len(calls) - 1, len(replies) - 1)]
        return (r, "mock-model") if r is not None else (None, "Engine A: failed")

    return fake, calls


def _markdown_output(sec):
    return (
        "## 1. Executive Summary\n" + sec["ringkasan"] + "\n\n## 2. Comparison Across Models\n" + sec["perbandingan"]
        + "\n\n## 3. Strengths and Weaknesses\n" + sec["kelebihan_kelemahan"] + "\n\n## 5. Risk Analysis\n" + sec["risiko"]
        + "\n\n## 6. Consistency Check\n" + sec["konsistensi"]
    )


@pytest.mark.parametrize("variant", ["complete", "truncated", "markdown_only", "fenced", "only_summary", "garbage"])
def test_run_analysis_same_guarantee_for_every_model_style(payload, variant):
    full = _complete_sections(payload)
    as_json = json.dumps(full, ensure_ascii=False)
    replies = {
        "complete": [as_json],
        "truncated": [as_json[: len(as_json) // 2]],
        "markdown_only": [_markdown_output(full)],
        "fenced": ["```json\n" + as_json + "\n```"],
        "only_summary": [json.dumps({"ringkasan": full["ringkasan"]})],
        "garbage": ["Sorry, I cannot help with that."],
    }[variant]
    fake, calls = _fake_llm(replies)
    with patch.object(analyze, "call_llm", fake):
        res = run_analysis(payload, api_key="k", provider="gemini")
    assert res["success"]
    _assert_all_present(res["sections"], payload)
    md = res["markdown"]
    for heading in ["## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6."]:
        assert heading in md
    assert "not available" not in md
    assert not md.lstrip().startswith("{")
    assert len(calls) == 1, "A report costs exactly one request: there is no repair call"
    if variant in ("complete", "fenced"):
        assert res["notes"] == []
    else:
        assert res["notes"], "The user is told when sections were filled automatically"


def test_run_analysis_passes_keys_and_engine_selection(payload):
    full = _complete_sections(payload)
    fake, calls = _fake_llm([json.dumps(full, ensure_ascii=False)])
    with patch.object(analyze, "call_llm", fake):
        run_analysis(payload, api_key="k", provider="openrouter", model="dots-studio/dots-3-note-preview:free",
                     keys={"gemini": "g", "openrouter": "o"})
    assert calls[0]["model"] == "dots-studio/dots-3-note-preview:free"
    assert calls[0]["keys"] == {"gemini": "g", "openrouter": "o"}
    assert calls[0]["max_tokens"] == analyze.ANALYSIS_MAX_TOKENS


def test_run_analysis_notes_which_engine_answered_after_a_failure(payload):
    full = _complete_sections(payload)

    def fake(messages, attempts=None, **kw):
        attempts.append("Gemini 4 Hydrogen: daily free quota is used up. It resets in about 19h43m.")
        return json.dumps(full, ensure_ascii=False), "Nemotron 3 Ultra 550B (OpenRouter, free)"

    with patch.object(analyze, "call_llm", fake):
        res = run_analysis(payload, api_key="k", provider="gemini")
    assert res["success"] and res["model_used"].startswith("Nemotron 3 Ultra")
    note = " ".join(res["notes"])
    assert "daily free quota" in note and "Answered by: Nemotron 3 Ultra" in note
    assert res["attempts"] and "Nemotron 3 Ultra" in res["markdown"]


def test_run_analysis_failure_lists_every_engine(payload):
    def fake(messages, attempts=None, **kw):
        attempts.extend(["Gemini 4 Hydrogen: daily free quota is used up.", "Dots3-Note 280B: rate-limited right now."])
        return None, "unused"

    with patch.object(analyze, "call_llm", fake):
        res = run_analysis(payload, api_key="k", provider="gemini")
    assert res["success"] is False
    assert "1) Gemini 4 Hydrogen" in res["error"] and "2) Dots3-Note" in res["error"]
    assert "failed" in res["markdown"].lower()


def test_run_analysis_failure_when_provider_returns_nothing(payload):
    fake, _ = _fake_llm([None])
    with patch.object(analyze, "call_llm", fake):
        res = run_analysis(payload, api_key="k", provider="gemini")
    assert res["success"] is False and "failed" in res["markdown"].lower()


def test_generate_markdown_never_inserts_hardcoded_products():
    md = generate_markdown_from_sections({}, "mock", [])
    for bad in HARDCODED + ["A6", "A2"]:
        assert bad not in md, bad
    assert "(not stated)" in md


def test_prompt_is_generic_and_demands_all_sections():
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent / "prompts" / "analysis_system.md").read_text(encoding="utf-8")
    for bad in HARDCODED + ["A6", "A2", "GPU"]:
        assert bad not in text, bad
    for key in ["ringkasan", "perbandingan", "kelebihan_kelemahan", "rekomendasi", "risiko", "konsistensi",
                "alternative", "backup_alternative", "backup_condition", "reasons"]:
        assert f'"{key}"' in text
    assert "REQUIRED" in text and "EACH group method" in text


def test_old_indonesian_prompt_files_are_gone():
    from pathlib import Path

    prompts = Path(__file__).resolve().parent.parent / "prompts"
    assert not (prompts / "analisis_sistem.md").exists()
    assert not (prompts / "chat_sistem.md").exists()
    assert (prompts / "chat_system.md").exists()


def test_payload_company_has_no_hardcoded_default():
    s = ce.blank_session().model_copy(update={"company": None})
    assert build_llm_payload(s, run_all(ce.apply_value_table(s, {a.id: {c.id: 1.0 + i + j for j, c in enumerate(s.criteria)} for i, a in enumerate(s.alternatives)})))["decision"]["company"] == ""


def test_normalize_sections_is_idempotent(payload):
    once = normalize_sections(_complete_sections(payload), payload)
    twice = normalize_sections(once, payload)
    assert once == twice
