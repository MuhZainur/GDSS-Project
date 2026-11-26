import json
import urllib.error
from io import BytesIO
from unittest.mock import patch, MagicMock

import pytest

from llm import client
from llm.client import (
    OPENROUTER_FREE_MODELS,
    build_chain,
    call_gemini,
    call_llm,
    call_openrouter,
    explain_http_error,
    get_gemini_models,
    get_openrouter_models,
    is_allowed_openrouter_model,
)

NEMOTRON_ULTRA = "nvidia/nemotron-3-ultra-550b-a55b:free"
DOTS = "dots-studio/dots-3-note-preview:free"
NEMOTRON_VL = "nvidia/nemotron-3.5-super-vl:free"
ERNIE = "baidu/ernie-5.5-flash-preview:free"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """The developer's real .env must never change what these tests see."""
    for var in ("OPENROUTER_MODELS", "GEMINI_MODELS", "GEMINI_MODEL", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(var, raising=False)


def _resp(obj):
    """A fake urlopen response usable as a context manager."""
    m = MagicMock()
    m.read.return_value = json.dumps(obj).encode("utf-8")
    m.__enter__.return_value = m
    return m


def _http_error(code, body=""):
    return urllib.error.HTTPError("u", code, "err", {}, BytesIO(body.encode("utf-8")))


# ── Model lists ──────────────────────────────────────────────────────────────
def test_gemini_is_only_hydrogen_low_thinking():
    assert get_gemini_models() == ["gemini-4-hydrogen"]
    assert client.GEMINI_THINKING_LEVEL == "low"
    assert client.DEFAULT_GEMINI_MODELS == ["gemini-4-hydrogen"]


def test_gemini_env_override_is_ignored(monkeypatch):
    monkeypatch.setenv("GEMINI_MODELS", "gemini-2.5-flash,gemini-2.5-pro")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    assert get_gemini_models() == ["gemini-4-hydrogen"]


def test_no_old_gemini_models_left_in_source():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for rel in ["llm/client.py", "app/pages_/assistant.py", ".env.example"]:
        text = (root / rel).read_text(encoding="utf-8")
        for old in ["gemini-2.5", "gemini-flash-latest", "gemini-1.5", "gemini-2.0"]:
            assert old not in text, f"{old} is still in {rel}"


def test_openrouter_default_list_is_the_four_large_free_models():
    models = get_openrouter_models()
    assert models == [NEMOTRON_ULTRA, DOTS, NEMOTRON_VL, ERNIE]
    for m in OPENROUTER_FREE_MODELS:
        assert m.id.endswith(":free")
        assert m.total_b > 29, m.id
        assert m.active_b is None or m.active_b >= 10, m.id
        assert is_allowed_openrouter_model(m.id)


def test_gemma_and_inkling_are_removed_everywhere():
    from pathlib import Path

    assert not is_allowed_openrouter_model("google/gemma-4-31b-it:free")
    assert not is_allowed_openrouter_model("thinkingmachines/inkling-2-small:free")
    root = Path(__file__).resolve().parent.parent
    for rel in ["app/pages_/assistant.py", ".env.example"]:
        text = (root / rel).read_text(encoding="utf-8").lower()
        assert "inkling-2-small:free" not in text, rel
        assert "gemma-4-31b-it:free" not in text, rel
    from app.pages_.assistant import AI_MODELS

    assert not any("gemma" in k.lower() or "inkling" in k.lower() for k in AI_MODELS)


@pytest.mark.parametrize("bad", [
    "google/gemma-4-26b-a4b-it:free",             # 26B total
    "nvidia/nemotron-3.5-lightning:free",         # small active size
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",  # 3B active
    "xingchen-agi/xing4.0-29b-a4b:free",          # 29B, not above 29B
    "nvidia/nemotron-3-ultra-550b-a55b",          # not :free
    "", None,
])
def test_openrouter_disallows_small_or_paid_models(bad):
    assert not is_allowed_openrouter_model(bad)


def test_openrouter_env_override_can_only_narrow_or_reorder(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODELS", f"google/gemma-4-26b-a4b-it:free,{DOTS},{NEMOTRON_ULTRA}")
    assert get_openrouter_models() == [DOTS, NEMOTRON_ULTRA]
    monkeypatch.setenv("OPENROUTER_MODELS", "google/gemma-4-26b-a4b-it:free")  # all rejected -> default
    assert get_openrouter_models() == [m.id for m in OPENROUTER_FREE_MODELS]


def test_openrouter_rejects_disallowed_model_without_network():
    with patch("llm.client.urllib.request.urlopen") as uo:
        content, msg = call_openrouter([{"role": "user", "content": "hi"}], model="google/gemma-4-26b-a4b-it:free", api_key="k")
    assert content is None and "not allowed" in msg
    uo.assert_not_called()


# ── Gemini request ───────────────────────────────────────────────────────────
def _gemini_ok(text="Hello"):
    return _resp({"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]})


def test_gemini_request_shape_hydrogen_low_thinking():
    with patch("llm.client.urllib.request.urlopen", return_value=_gemini_ok("Answer")) as uo:
        content, used = call_gemini(
            [{"role": "system", "content": "Rules"}, {"role": "user", "content": "Hello"}],
            model="gemini-2.5-pro",  # must be ignored
            api_key="SECRET-KEY", json_mode=True, max_tokens=1000,
        )
    assert content == "Answer" and "Gemini 4 Hydrogen" in used and "low" in used
    req = uo.call_args[0][0]
    assert req.full_url.endswith("/models/gemini-4-hydrogen:generateContent")
    assert "SECRET-KEY" not in req.full_url, "The key must not be in the URL"
    assert req.get_header("X-goog-api-key") == "SECRET-KEY"
    body = json.loads(req.data)
    gc = body["generationConfig"]
    assert gc["thinkingConfig"] == {"thinkingLevel": "low"}
    assert gc["responseMimeType"] == "application/json"
    assert gc["maxOutputTokens"] >= 1000 + 4096, "Thinking tokens need extra room"
    assert body["system_instruction"]["parts"][0]["text"] == "Rules"


def test_gemini_joins_text_parts_and_skips_thoughts():
    parts = [{"text": "secret thoughts", "thought": True}, {"text": "Part one. "}, {"text": "Part two."}]
    ok = _resp({"candidates": [{"content": {"parts": parts}}]})
    with patch("llm.client.urllib.request.urlopen", return_value=ok):
        content, _ = call_gemini([{"role": "user", "content": "x"}], api_key="k")
    assert content == "Part one. Part two."


def test_gemini_empty_text_is_failure_not_blank_answer():
    empty = _resp({"candidates": [{"content": {"parts": [{"thought": True, "text": "thinking"}]}, "finishReason": "MAX_TOKENS"}]})
    with patch("llm.client.urllib.request.urlopen", return_value=empty) as uo:
        content, msg = call_gemini([{"role": "user", "content": "x"}], api_key="k")
    assert content is None and "MAX_TOKENS" in msg
    assert uo.call_count == 1, "An empty response must not be repeated"


def test_gemini_missing_key_and_http_error():
    content, msg = call_gemini([{"role": "user", "content": "x"}])
    assert content is None and "no API key" in msg
    with patch("llm.client.urllib.request.urlopen", side_effect=_http_error(400)):
        content, msg = call_gemini([{"role": "user", "content": "x"}], api_key="k")
    assert content is None and "400" in msg


# ── Error policy: 429 is never retried ───────────────────────────────────────
DAILY_429 = json.dumps({"error": {"code": 429, "message": "Quota exceeded for metric: generate_content_free_tier_requests, "
                                  "limit: 20, model: gemini-4-hydrogen. Please retry in 19h43m.", "status": "RESOURCE_EXHAUSTED",
                                  "details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}})


def test_gemini_429_is_not_retried_and_explains_daily_quota():
    with patch("llm.client.urllib.request.urlopen", side_effect=_http_error(429, DAILY_429)) as uo, patch("llm.client.time.sleep") as sl:
        content, msg = call_gemini([{"role": "user", "content": "x"}], api_key="k")
    assert content is None
    assert uo.call_count == 1 and sl.call_count == 0
    assert "daily free quota is used up" in msg and "19h43m" in msg


def test_openrouter_429_and_403_are_not_retried():
    for code, phrase in ((429, "rate-limited"), (403, "access denied")):
        with patch("llm.client.urllib.request.urlopen", side_effect=_http_error(code, "{}")) as uo, patch("llm.client.time.sleep") as sl:
            content, msg = call_openrouter([{"role": "user", "content": "x"}], model=DOTS, api_key="k")
        assert content is None and uo.call_count == 1 and sl.call_count == 0, code
        assert phrase in msg and "Dots3-Note" in msg


def test_5xx_retries_once_then_reports_friendly_error():
    with patch("llm.client.urllib.request.urlopen", side_effect=_http_error(503)) as uo, patch("llm.client.time.sleep") as sl:
        content, msg = call_gemini([{"role": "user", "content": "x"}], api_key="k")
    assert content is None and uo.call_count == 2 and sl.call_count == 1
    assert "busy or down" in msg and "503" in msg


def test_explain_http_error_messages():
    assert "key was rejected" in explain_http_error("X", 401)
    assert "not available" in explain_http_error("X", 404)
    assert "daily free quota" in explain_http_error("X", 429, "per day limit")
    assert "rate-limited" in explain_http_error("X", 429, "")
    assert "HTTP 418" in explain_http_error("X", 418, "")


# ── OpenRouter request ───────────────────────────────────────────────────────
def test_openrouter_does_not_use_reasoning_text_as_answer():
    thin = _resp({"choices": [{"message": {"content": "", "reasoning": "thinking notes"}}]})
    with patch("llm.client.urllib.request.urlopen", return_value=thin):
        content, msg = call_openrouter([{"role": "user", "content": "x"}], model=DOTS, api_key="k")
    assert content is None and "no answer text" in msg


def test_openrouter_auto_tries_allowed_models_in_order():
    seen = []

    def fake(req, timeout=0):
        seen.append(json.loads(req.data)["model"])
        raise _http_error(404)

    with patch("llm.client.urllib.request.urlopen", side_effect=fake):
        content, msg = call_openrouter([{"role": "user", "content": "x"}], api_key="k")
    assert content is None
    assert seen == [m.id for m in OPENROUTER_FREE_MODELS]
    assert len(msg.splitlines()) == len(OPENROUTER_FREE_MODELS)


def test_openrouter_json_mode_only_for_models_that_support_it():
    ok = _resp({"choices": [{"message": {"content": "{}"}}]})
    bodies = {}

    def fake(req, timeout=0):
        body = json.loads(req.data)
        bodies[body["model"]] = body
        return ok

    with patch("llm.client.urllib.request.urlopen", side_effect=fake):
        call_openrouter([{"role": "user", "content": "x"}], model=NEMOTRON_ULTRA, api_key="k", json_mode=True)
        call_openrouter([{"role": "user", "content": "x"}], model=DOTS, api_key="k", json_mode=True)
    assert "response_format" not in bodies[NEMOTRON_ULTRA]
    assert bodies[DOTS]["response_format"] == {"type": "json_object"}


# ── Fallback chain ───────────────────────────────────────────────────────────
def test_build_chain_orders():
    g = build_chain("gemini", None)
    assert g[0] == ("gemini", "gemini-4-hydrogen")
    assert [m for _, m in g[1:]] == [NEMOTRON_ULTRA, DOTS, NEMOTRON_VL, ERNIE]
    o = build_chain("openrouter", NEMOTRON_VL)
    assert o[0] == ("openrouter", NEMOTRON_VL)
    assert o[-1] == ("gemini", "gemini-4-hydrogen")
    assert [m for _, m in o[:-1]] == [NEMOTRON_VL, NEMOTRON_ULTRA, DOTS, ERNIE]
    auto = build_chain("openrouter", None)
    assert [m for _, m in auto[:-1]] == [NEMOTRON_ULTRA, DOTS, NEMOTRON_VL, ERNIE]
    assert build_chain("auto", None)[0][0] == "gemini"
    # a disallowed model id is ignored instead of being called
    assert build_chain("openrouter", "google/gemma-4-31b-it:free")[0] == ("openrouter", NEMOTRON_ULTRA)


def test_call_llm_dispatch_gemini():
    with patch("llm.client.call_gemini") as mock_gemini:
        mock_gemini.return_value = ("Gemini answer", "Gemini 4 Hydrogen (thinking low)")
        content, used = call_llm([{"role": "user", "content": "Hello"}], provider="gemini", api_key="k")
        assert content == "Gemini answer" and "Gemini" in used
        mock_gemini.assert_called_once()


def test_call_llm_dispatch_openrouter_uses_the_chosen_model_first():
    with patch("llm.client.call_openrouter") as mock_or, patch("llm.client.call_gemini") as mock_g:
        mock_or.return_value = ("OR answer", "Dots3-Note 280B (OpenRouter, free)")
        content, used = call_llm([{"role": "user", "content": "Hello"}], provider="openrouter", model=DOTS, api_key="k")
    assert content == "OR answer" and "Dots3" in used
    assert mock_or.call_args[0][1] == DOTS
    mock_g.assert_not_called()


def test_gemini_quota_falls_back_to_openrouter_and_records_why():
    attempts = []
    with patch("llm.client.call_gemini") as mock_g, patch("llm.client.call_openrouter") as mock_or:
        mock_g.return_value = (None, "Gemini 4 Hydrogen: daily free quota is used up. It resets in about 19h43m.")
        mock_or.return_value = ("fallback answer", "Nemotron 3 Ultra 550B (OpenRouter, free)")
        content, used = call_llm(
            [{"role": "user", "content": "Hello"}], provider="gemini", api_key="g",
            keys={"gemini": "g", "openrouter": "o"}, attempts=attempts,
        )
    assert content == "fallback answer" and "Nemotron 3 Ultra" in used
    assert len(attempts) == 1 and "daily free quota" in attempts[0]
    assert mock_or.call_args[0][1] == NEMOTRON_ULTRA


def test_chosen_openrouter_model_fails_then_next_models_then_gemini():
    called = []

    def fake_or(messages, model, *a, **k):
        called.append(model)
        return None, f"{model}: rate-limited"

    with patch("llm.client.call_openrouter", side_effect=fake_or), patch("llm.client.call_gemini") as mock_g:
        mock_g.return_value = ("last resort", "Gemini 4 Hydrogen (thinking low)")
        content, used = call_llm(
            [{"role": "user", "content": "x"}], provider="openrouter", model=DOTS, api_key="o",
            keys={"gemini": "g", "openrouter": "o"},
        )
    assert content == "last resort"
    assert called == [DOTS, NEMOTRON_ULTRA, NEMOTRON_VL, ERNIE]


def test_engines_without_a_key_are_skipped():
    with patch("llm.client.call_gemini") as mock_g, patch("llm.client.call_openrouter") as mock_or:
        mock_or.return_value = ("ok", "x")
        content, _ = call_llm([{"role": "user", "content": "x"}], provider="gemini", api_key="", keys={"openrouter": "o"})
    mock_g.assert_not_called()
    assert content == "ok"


def test_all_engines_failing_returns_one_line_per_engine():
    with patch("llm.client.call_gemini", return_value=(None, "Gemini: quota")), \
         patch("llm.client.call_openrouter", side_effect=lambda m, model, *a, **k: (None, f"{model}: down")):
        content, msg = call_llm([{"role": "user", "content": "x"}], provider="gemini", api_key="g", keys={"openrouter": "o"})
    assert content is None
    lines = msg.splitlines()
    assert lines[0] == "Gemini: quota" and len(lines) == 1 + len(OPENROUTER_FREE_MODELS)


def test_fallback_can_be_turned_off():
    with patch("llm.client.call_gemini", return_value=(None, "Gemini: quota")), patch("llm.client.call_openrouter") as mock_or:
        content, msg = call_llm([{"role": "user", "content": "x"}], provider="gemini", api_key="g",
                                keys={"openrouter": "o"}, fallback=False)
    assert content is None and msg == "Gemini: quota"
    mock_or.assert_not_called()


def test_no_keys_at_all_gives_a_clear_message():
    content, msg = call_llm([{"role": "user", "content": "x"}], provider="gemini")
    assert content is None and "no API key" in msg


def test_reasoning_model_gets_extra_token_headroom_others_do_not():
    """Nemotron 3.5 Super VL spends thousands of tokens on hidden reasoning; without headroom its answer is cut off."""
    ok = _resp({"choices": [{"message": {"content": "{}"}}]})
    sent = {}

    def fake(req, timeout=0):
        body = json.loads(req.data)
        sent[body["model"]] = body["max_tokens"]
        return ok

    with patch("llm.client.urllib.request.urlopen", side_effect=fake):
        call_openrouter([{"role": "user", "content": "x"}], model=NEMOTRON_VL, api_key="k", max_tokens=6000)
        call_openrouter([{"role": "user", "content": "x"}], model=DOTS, api_key="k", max_tokens=6000)
    assert sent[NEMOTRON_VL] == 6000 + 8000
    assert sent[DOTS] == 6000
