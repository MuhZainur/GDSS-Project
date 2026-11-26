"""Saved AI reports (per run and engine) and the chat layer's engine-fallback reporting."""
import json

import pytest

import app.repository as repo
from llm import chat


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    monkeypatch.setattr(repo, "STORAGE_DIR", storage)
    monkeypatch.setattr(repo, "SESSIONS_DIR", storage / "sessions")
    monkeypatch.setattr(repo, "RUNS_DIR", storage / "runs")
    monkeypatch.setattr(repo, "CHATS_DIR", storage / "chats")
    monkeypatch.setattr(chat, "save_chat", repo.save_chat)
    monkeypatch.setattr(chat, "load_chat", repo.load_chat)


# ── Saved reports ────────────────────────────────────────────────────────────
def test_save_and_load_analysis_roundtrip():
    data = {"success": True, "model_used": "x", "sections": {"ringkasan": "Text with ünïcode"}}
    path = repo.save_analysis("run-1", "gemini_gemini-4-hydrogen", data)
    assert path.name == "analysis_gemini_gemini-4-hydrogen.json" and path.exists()
    assert repo.load_analysis("run-1", "gemini_gemini-4-hydrogen") == data


def test_each_engine_has_its_own_saved_report():
    repo.save_analysis("run-1", "gemini_gemini-4-hydrogen", {"success": True, "model_used": "A"})
    repo.save_analysis("run-1", "openrouter_None", {"success": True, "model_used": "B"})
    assert repo.load_analysis("run-1", "gemini_gemini-4-hydrogen")["model_used"] == "A"
    assert repo.load_analysis("run-1", "openrouter_None")["model_used"] == "B"
    assert repo.load_analysis("run-1", "openrouter_other") is None


def test_failed_or_corrupt_reports_are_never_loaded():
    repo.save_analysis("run-2", "e", {"success": False, "error": "quota"})
    assert repo.load_analysis("run-2", "e") is None
    repo.save_analysis("run-3", "e", {"success": True})
    (repo.RUNS_DIR / "run-3" / "analysis_e.json").write_text("{not json", encoding="utf-8")
    assert repo.load_analysis("run-3", "e") is None
    assert repo.load_analysis("missing-run", "e") is None


def test_saved_analysis_cannot_escape_the_storage_folder(tmp_path):
    repo.save_analysis("../../evil", "../x", {"success": True})
    assert not (tmp_path / "evil").exists()
    inside = [p for p in (tmp_path / "storage").rglob("analysis_*.json")]
    assert len(inside) == 1 and (tmp_path / "storage") in inside[0].parents


# ── Chat: who answered ───────────────────────────────────────────────────────
def _chat(monkeypatch, fake_call):
    monkeypatch.setattr(chat, "call_llm", fake_call)
    return chat.chat_step(run_id="r1", chat_id="c1", user_message="Why?", payload={"a": 1}, api_key="k", provider="gemini",
                          keys={"gemini": "g", "openrouter": "o"})


def test_chat_reports_the_engine_that_answered(monkeypatch):
    reply, sources, used = _chat(monkeypatch, lambda **kw: ("A plain answer", "Gemini 4 Hydrogen (thinking low)"))
    assert reply == "A plain answer" and used == "Gemini 4 Hydrogen (thinking low)"


def test_chat_explains_fallback_when_the_selected_engine_failed(monkeypatch):
    def fake(**kw):
        kw["attempts"].append("Gemini 4 Hydrogen: daily free quota is used up.")
        return "Answer from the backup", "Nemotron 3 Ultra 550B (OpenRouter, free)"

    reply, _, used = _chat(monkeypatch, fake)
    assert reply == "Answer from the backup"
    assert used.startswith("Nemotron 3 Ultra") and "the selected engine failed" in used and "daily free quota" in used
    saved = repo.load_chat("r1", "c1")
    assert saved["messages"][-1]["model_used"] == used


def test_chat_failure_is_a_friendly_english_message(monkeypatch):
    reply, _, used = _chat(monkeypatch, lambda **kw: (None, "Gemini 4 Hydrogen: daily free quota is used up."))
    assert reply.startswith("Sorry, the assistant could not answer.") and "daily free quota" in reply
    assert used == "no engine answered"


def test_chat_passes_keys_and_uses_english_prompt(monkeypatch):
    seen = {}

    def fake(**kw):
        seen.update(kw)
        return "ok", "x"

    _chat(monkeypatch, fake)
    assert seen["keys"] == {"gemini": "g", "openrouter": "o"}
    system = seen["messages"][0]["content"]
    assert "GDSS" in system and " yang " not in system and " dan " not in system


def test_sanitize_chat_reply_unwraps_json_answers():
    assert chat.sanitize_chat_reply('{"answer": "Hello"}') == "Hello"
    assert chat.sanitize_chat_reply('```json\n{"response": "Hi"}\n```') == "Hi"
    assert chat.sanitize_chat_reply("Just text") == "Just text"
    assert chat.sanitize_chat_reply("") == ""
