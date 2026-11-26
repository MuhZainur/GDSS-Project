import os
import time
import json
import re
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

# ── Google Gemini ────────────────────────────────────────────────────────────
# The only Gemini model in use. Sources: https://ai.google.dev/gemini-api/docs/models and
# https://ai.google.dev/gemini-api/docs/thinking (thinking levels: low, medium, high, xhigh;
# "minimal" is rejected by the API with HTTP 400 for this model).
GEMINI_MODEL = "gemini-4-hydrogen"
GEMINI_LABEL = "Gemini 4 Hydrogen"
GEMINI_THINKING_LEVEL = "low"
# In Gemini, maxOutputTokens covers thinking tokens + the answer. `max_tokens` below means
# "room for the visible answer"; this headroom is added on top for thinking.
GEMINI_THINKING_HEADROOM = 6144
DEFAULT_GEMINI_MODELS = [GEMINI_MODEL]

# ── OpenRouter: free models above 29B parameters only ────────────────────────
# Rule: the id must end in ":free", total parameters must be above 29B and, when announced, active
# parameters must be at least 10B so answers are not shallow. Checked against
# https://openrouter.ai/api/v1/models on 2026-11-19 and by live calls. The free lineup changes often;
# run scripts/check_free_models.py before a demo. Removed after live testing: gemma-4-31b-it (shared
# upstream pool is rate-limited all the time) and inkling-2-small (only served to "agentic harness" apps).
MIN_TOTAL_PARAMS_B = 30
MIN_ACTIVE_PARAMS_B = 10


@dataclass(frozen=True)
class FreeModel:
    id: str
    label: str
    total_b: float
    active_b: Optional[float]  # None = not announced
    json_mode: bool            # supports response_format JSON
    thinking_headroom: int = 0  # extra completion tokens for hidden reasoning (counted inside max_tokens by the API)


OPENROUTER_FREE_MODELS: Tuple[FreeModel, ...] = (
    FreeModel("nvidia/nemotron-3-ultra-550b-a55b:free", "Nemotron 3 Ultra 550B", 550, 55, False),
    FreeModel("dots-studio/dots-3-note-preview:free", "Dots3-Note 280B", 280, 16, True),
    # Live test 2026-11-19: with max_tokens=6000 this model spent ~5,700 tokens on hidden reasoning and the answer was cut
    # off after two sections (finish_reason=length). With 6000 + 8000 it finished with all six sections (~11,500 tokens).
    FreeModel("nvidia/nemotron-3.5-super-vl:free", "Nemotron 3.5 Super VL 120B", 120, 12, True, thinking_headroom=8000),
    FreeModel("baidu/ernie-5.5-flash-preview:free", "ERNIE 5.5 Flash 280B", 280, None, True),
)

_FREE_BY_ID = {m.id: m for m in OPENROUTER_FREE_MODELS}
DEFAULT_OPENROUTER_MODELS = [m.id for m in OPENROUTER_FREE_MODELS]


def is_allowed_openrouter_model(model_id: str) -> bool:
    m = _FREE_BY_ID.get((model_id or "").strip())
    if m is None or not m.id.endswith(":free"):
        return False
    return m.total_b >= MIN_TOTAL_PARAMS_B and (m.active_b is None or m.active_b >= MIN_ACTIVE_PARAMS_B)


def openrouter_label(model_id: str) -> str:
    m = _FREE_BY_ID.get(model_id)
    return m.label if m else model_id


def get_gemini_models() -> List[str]:
    """Gemini models in use (only gemini-4-hydrogen)."""
    return [GEMINI_MODEL]


def get_openrouter_models() -> List[str]:
    """
    OpenRouter models that may be used. OPENROUTER_MODELS in .env can only reorder or narrow this list;
    ids outside it (for example anything below 30B) are ignored.
    """
    env_models = os.getenv("OPENROUTER_MODELS")
    if env_models:
        chosen = [m.strip() for m in env_models.split(",") if is_allowed_openrouter_model(m.strip())]
        if chosen:
            return chosen
    return list(DEFAULT_OPENROUTER_MODELS)


# Backward-compatible aliases
get_model_list = get_openrouter_models
DEFAULT_FREE_MODELS = DEFAULT_OPENROUTER_MODELS


# ── Error explanations ───────────────────────────────────────────────────────
def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def _error_message(body: str) -> str:
    """Short human message from a JSON error body (never includes ids or raw metadata)."""
    try:
        err = json.loads(body).get("error", {})
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
    except Exception:
        msg = body or ""
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg[:140]


def explain_http_error(label: str, code: int, body: str = "") -> str:
    """Plain-English reason for a failed call. 429 and 403 are never retried."""
    low = (body or "").lower()
    if code == 429:
        daily = "perday" in low or "per day" in low or "per-day" in low
        if daily:
            m = re.search(r"retry in ((?:\d+h)?(?:\d+m)?)", body or "")
            reset = f" It resets in about {m.group(1)}." if m and m.group(1) else " It resets within a day."
            return f"{label}: daily free quota is used up.{reset}"
        return f"{label}: rate-limited right now (the shared free pool is busy)."
    if code == 403:
        return f"{label}: access denied (the provider does not serve this model to this app or key)."
    if code == 401:
        return f"{label}: the API key was rejected."
    if code == 404:
        return f"{label}: model not available right now."
    if code in (500, 502, 503, 504):
        return f"{label}: the service is busy or down (HTTP {code})."
    detail = _error_message(body)
    return f"{label}: request failed (HTTP {code})" + (f": {detail}" if detail else ".")


# ── Gemini call ──────────────────────────────────────────────────────────────
def call_gemini(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2500,
    api_key: Optional[str] = None,
    json_mode: bool = False
) -> Tuple[Optional[str], Optional[str]]:
    """
    Calls Gemini 4 Hydrogen (thinking level: low) through generateContent. Any `model` other than
    gemini-4-hydrogen is ignored. Returns (text, answering engine) or (None, error message).
    """
    key = (api_key or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key:
        return None, f"{GEMINI_LABEL}: no API key. Enter a Google Gemini key in the API key field or set GOOGLE_API_KEY in .env."

    system_parts = []
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue
        if role == "system":
            system_parts.append({"text": content})
        else:
            gemini_role = "model" if role == "assistant" else "user"
            if contents and contents[-1]["role"] == gemini_role:
                contents[-1]["parts"].append({"text": content})
            else:
                contents.append({"role": gemini_role, "parts": [{"text": content}]})
    if not contents:
        contents.append({"role": "user", "parts": [{"text": "Begin."}]})

    gen_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": int(max_tokens) + GEMINI_THINKING_HEADROOM,
        "thinkingConfig": {"thinkingLevel": GEMINI_THINKING_LEVEL},
    }
    if json_mode:
        gen_config["responseMimeType"] = "application/json"

    payload: Dict[str, Any] = {"contents": contents, "generationConfig": gen_config}
    if system_parts:
        payload["system_instruction"] = {"parts": system_parts}

    req_data = json.dumps(payload).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    last_err = ""

    for attempt in range(2):
        try:
            # The key travels in a header, not in the URL, so it never shows up in logs or error messages.
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json", "x-goog-api-key": key},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                res_json = json.loads(response.read().decode("utf-8"))

            candidates = res_json.get("candidates", [])
            if candidates:
                cand = candidates[0]
                parts = cand.get("content", {}).get("parts", []) or []
                # Ignore thinking parts (thought=true); join the rest.
                text = _strip_think("".join(p.get("text", "") for p in parts if p.get("text") and not p.get("thought")))
                if text:
                    return text, f"{GEMINI_LABEL} (thinking {GEMINI_THINKING_LEVEL})"
                reason = cand.get("finishReason", "") or "empty"
                last_err = f"{GEMINI_LABEL}: no answer text came back (finishReason={reason})."
                if reason == "MAX_TOKENS":
                    last_err += " The token limit ran out while thinking."
            else:
                block = res_json.get("promptFeedback", {}).get("blockReason")
                last_err = f"{GEMINI_LABEL}: no answer came back" + (f" (blocked: {block})." if block else ".")
            break  # a valid but empty response: repeating the same input will not help
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore") if e.fp else ""
            last_err = explain_http_error(GEMINI_LABEL, e.code, body)
            if e.code in (500, 502, 503, 504) and attempt == 0:
                time.sleep(2)  # transient: retry once. 429/403/etc. are never retried.
                continue
            break
        except Exception as e:
            last_err = f"{GEMINI_LABEL}: connection problem ({type(e).__name__})."
            if attempt == 0:
                time.sleep(1)
                continue
            break

    return None, last_err


# ── OpenRouter call ──────────────────────────────────────────────────────────
def call_openrouter(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2500,
    api_key: Optional[str] = None,
    json_mode: bool = False
) -> Tuple[Optional[str], Optional[str]]:
    """
    Calls one allowed OpenRouter free model (see OPENROUTER_FREE_MODELS). With model=None the allowed
    models are tried in order. Returns (text, answering engine) or (None, error message).
    """
    key = (api_key or os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not key:
        return None, "OpenRouter: no API key. Enter an OpenRouter key in the API key field or set OPENROUTER_API_KEY in .env."

    if model is None:
        errors = []
        for m in get_openrouter_models():
            content, used = call_openrouter(messages, m, temperature, max_tokens, key, json_mode)
            if content:
                return content, used
            errors.append(used or "")
        return None, "\n".join(errors)

    if not is_allowed_openrouter_model(model):
        return None, (
            f"{model}: not allowed. Only free (:free) models above 29B total parameters "
            "with at least 10B active parameters can be used."
        )

    label = openrouter_label(model)
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Decision Room GDSS",
        "Content-Type": "application/json",
    }
    budget = int(max_tokens) + _FREE_BY_ID[model].thinking_headroom
    body: Dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": budget}
    if json_mode and _FREE_BY_ID[model].json_mode:
        body["response_format"] = {"type": "json_object"}
    req_data = json.dumps(body).encode("utf-8")

    last_error = ""
    for attempt in range(2):
        try:
            req = urllib.request.Request(f"{base_url}/chat/completions", data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as response:
                res_json = json.loads(response.read().decode("utf-8"))

            if "error" in res_json:
                err = res_json["error"]
                code = err.get("code") if isinstance(err, dict) else None
                if isinstance(code, int):
                    return None, explain_http_error(label, code, json.dumps({"error": err}))
                return None, f"{label}: provider error: {_error_message(json.dumps({'error': err}))}"

            choices = res_json.get("choices", [])
            if choices:
                # The "reasoning" text is thinking notes, not an answer, so it is never used as one.
                content = _strip_think(choices[0].get("message", {}).get("content", "") or "")
                if content:
                    return content, f"{label} (OpenRouter, free)"
            return None, f"{label}: no answer text came back (the model may have run out of tokens while thinking)."
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore") if e.fp else ""
            last_error = explain_http_error(label, e.code, err_body)
            if e.code in (500, 502, 503, 504) and attempt == 0:
                time.sleep(2)  # transient: retry once. 429/403/etc. are never retried.
                continue
            return None, last_error
        except Exception as e:
            last_error = f"{label}: connection problem ({type(e).__name__})."
            if attempt == 0:
                time.sleep(1)
                continue
    return None, last_error


# ── Dispatcher with automatic fallback ───────────────────────────────────────
def _selected_provider(provider: Optional[str]) -> str:
    p = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower().strip()
    return "openrouter" if p == "openrouter" else "gemini"  # "auto" = start with Gemini


def build_chain(provider: Optional[str], model: Optional[str]) -> List[Tuple[str, Optional[str]]]:
    """
    Order of engines to try. The selected engine goes first, then the other free models, and Gemini last
    when an OpenRouter model was chosen (its free quota is only 20 requests per day).
    """
    or_models = get_openrouter_models()
    if _selected_provider(provider) == "gemini":
        return [("gemini", GEMINI_MODEL)] + [("openrouter", m) for m in or_models]
    first = model if model and is_allowed_openrouter_model(model) else None
    ordered = ([first] if first else []) + [m for m in or_models if m != first]
    return [("openrouter", m) for m in ordered] + [("gemini", GEMINI_MODEL)]


def call_llm(
    messages: List[Dict[str, str]],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2500,
    api_key: Optional[str] = None,
    json_mode: bool = False,
    fallback: bool = True,
    keys: Optional[Dict[str, str]] = None,
    attempts: Optional[List[str]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Main LLM entry point. Tries the selected engine first; when it fails (quota, rate limit, access denied,
    outage) and `fallback` is on, moves on to the next engine in `build_chain`.

    `api_key` belongs to the selected provider; `keys` ({"gemini": ..., "openrouter": ...}) supplies keys for the
    other provider, and environment variables are the last resort. Engines without any key are skipped.
    Failures are appended to `attempts` (if given). Returns (text, answering engine); when every engine fails,
    (None, one line per failure).
    """
    selected = _selected_provider(provider)
    env = {"gemini": os.getenv("GOOGLE_API_KEY"), "openrouter": os.getenv("OPENROUTER_API_KEY")}

    def key_for(p: str) -> str:
        own = api_key if p == selected else None
        return (own or (keys or {}).get(p) or env[p] or "").strip()

    chain = build_chain(provider, model)
    if not fallback:
        chain = chain[:1]

    failures: List[str] = []
    for prov, mdl in chain:
        key = key_for(prov)
        if not key:
            if prov == selected and not failures:
                failures.append(
                    f"{GEMINI_LABEL if prov == 'gemini' else 'OpenRouter'}: no API key."
                    " Enter a key in the API key field or set it in .env."
                )
            continue
        if prov == "gemini":
            content, used = call_gemini(messages, GEMINI_MODEL, temperature, max_tokens, key, json_mode)
        else:
            content, used = call_openrouter(messages, mdl, temperature, max_tokens, key, json_mode)
        if content:
            if attempts is not None:
                attempts.extend(failures)
            return content, used
        failures.append(used or "Unknown error.")

    if attempts is not None:
        attempts.extend(failures)
    return None, "\n".join(failures) or "No engine is available: add an API key."
