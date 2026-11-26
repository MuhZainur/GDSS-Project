import re
import json
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from llm.client import call_llm
from llm.completeness import complete_sections


def extract_all_numbers_from_json(obj: Any) -> Set[float]:
    """Collects every numeric value from a JSON structure."""
    numbers = set()
    if isinstance(obj, (int, float)):
        numbers.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            numbers.update(extract_all_numbers_from_json(v))
    elif isinstance(obj, list):
        for item in obj:
            numbers.update(extract_all_numbers_from_json(item))
    return numbers


def validate_numbers_in_text(text: str, payload_numbers: Set[float]) -> List[str]:
    """
    Extracts decimal numbers from the LLM text and checks that they exist in the payload.
    Tolerance <= 0.005, or as a percentage (for example 16.11% vs 0.1611).
    Returns the unverified numbers (possible hallucinations).
    """
    decimal_pattern = re.compile(r'\b\d+\.\d+\b')
    found_strings = decimal_pattern.findall(text)

    unverified = []
    for s_num in set(found_strings):
        try:
            val = float(s_num)
            # Skip years such as 2026.0
            if 2020 <= val <= 2035:
                continue

            matched = False
            for p_num in payload_numbers:
                if abs(val - p_num) < 0.005 or abs(val / 100.0 - p_num) < 0.005 or abs(val - p_num * 100.0) < 0.5:
                    matched = True
                    break
            if not matched:
                unverified.append(s_num)
        except ValueError:
            pass

    return sorted(unverified)


def robust_extract_sections(content: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Multi-layer extractor so the response of ANY LLM is turned into a tidy sections structure
    and raw JSON is NEVER shown to the user.
    """
    sections: Dict[str, Any] = {}
    clean = content.strip()

    # 1. Remove a markdown code fence if present
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json|markdown)?\s*\n?", "", clean)
        clean = re.sub(r"\n?```\s*$", "", clean).strip()

    # 2. Try to parse JSON directly
    parsed_json = None
    if "{" in clean and "}" in clean:
        try:
            start_idx = clean.find("{")
            end_idx = clean.rfind("}")
            if start_idx != -1 and end_idx > start_idx:
                parsed_json = json.loads(clean[start_idx:end_idx + 1])
        except Exception:
            pass

    # 3. Try to repair JSON that was cut off by the token limit
    if not parsed_json and "{" in clean:
        for suffix in ['"}', '"\n}', '"]\n}', '"]\n}\n}', '\n}', '\n}\n}']:
            try:
                candidate = clean + suffix
                start_idx = candidate.find("{")
                parsed_json = json.loads(candidate[start_idx:])
                break
            except Exception:
                pass

    if isinstance(parsed_json, dict):
        sections = parsed_json

    # 4. If JSON parsing failed or keys are empty, fall back to a regex extractor
    keys = ["ringkasan", "perbandingan", "kelebihan_kelemahan", "rekomendasi", "risiko", "konsistensi"]
    missing_keys = [k for k in keys if k not in sections or not sections[k]]

    if missing_keys and ('"ringkasan"' in clean or '"perbandingan"' in clean or '"kelebihan_kelemahan"' in clean):
        for k in keys:
            if k in sections and sections[k]:
                continue
            other_keys = [x for x in keys if x != k]
            # Pattern 1: a string value (ends before the next key or the closing brace)
            p1 = r'\"' + k + r'\"\s*:\s*\"(.*?)(?=\"\s*,\s*\"(?:' + "|".join(other_keys) + r')\"|\"\s*\}|$)'
            m1 = re.search(p1, clean, re.DOTALL)
            if m1:
                val = m1.group(1)
                val = val.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
                sections[k] = val.strip()
            elif k == "rekomendasi":
                # Pattern 2: the recommendation as an object
                p_obj = r'\"rekomendasi\"\s*:\s*\{(.*?)(?:\}\s*,\s*\"|\}\s*\}|$)'
                m_obj = re.search(p_obj, clean, re.DOTALL)
                if m_obj:
                    try:
                        sections["rekomendasi"] = json.loads("{" + m_obj.group(1).rstrip(", \n") + "}")
                    except Exception:
                        pass

    # 5. If the output is plain Markdown instead of JSON
    if not sections or (len(sections) == 1 and "ringkasan" in sections and not any(k in sections for k in ["perbandingan", "kelebihan_kelemahan"])):
        md_sections = {}
        patterns = [
            ("ringkasan", r'(?:##\s*1\.[^\n]*\n|#+\s*(?:Executive\s+)?Summary[^\n]*\n)(.*?)(?=##\s*2|\Z)'),
            ("perbandingan", r'(?:##\s*2\.[^\n]*\n|#+\s*(?:Comparison|Across Methods)[^\n]*\n)(.*?)(?=##\s*3|\Z)'),
            ("kelebihan_kelemahan", r'(?:##\s*3\.[^\n]*\n|#+\s*Strengths[^\n]*\n)(.*?)(?=##\s*4|\Z)'),
            ("rekomendasi", r'(?:##\s*4\.[^\n]*\n|#+\s*Recommendation[^\n]*\n)(.*?)(?=##\s*5|\Z)'),
            ("risiko", r'(?:##\s*5\.[^\n]*\n|#+\s*Risks?[^\n]*\n)(.*?)(?=##\s*6|\Z)'),
            ("konsistensi", r'(?:##\s*6\.[^\n]*\n|#+\s*Consistency[^\n]*\n)(.*?)\Z'),
        ]
        for key, pat in patterns:
            m = re.search(pat, clean, re.DOTALL | re.IGNORECASE)
            if m:
                md_sections[key] = m.group(1).strip()
        for k, v in md_sections.items():
            if k not in sections or not sections[k]:
                sections[k] = v

    # 6. Completeness (empty recommendation, short sections, ...) is guaranteed by llm.completeness.complete_sections.

    # 7. Clean leftover quotes and escape characters
    for k in ["ringkasan", "perbandingan", "kelebihan_kelemahan", "risiko", "konsistensi"]:
        if k in sections and isinstance(sections[k], str):
            val = sections[k].strip()
            if val.startswith('"') and val.endswith('"') and len(val) > 1:
                val = val[1:-1]
            val = val.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
            sections[k] = val.strip()

    return sections


def generate_markdown_from_sections(
    sections: Dict[str, Any],
    model_used: str,
    unverified: List[str],
    notes: Optional[List[str]] = None,
) -> str:
    """Turns sections into a Markdown document. Missing parts are marked clearly, never filled with built-in names."""
    recom = sections.get("rekomendasi", {})
    if not isinstance(recom, dict):
        recom = {"alternative": str(recom)}
    recom_alt = recom.get("alternative") or "(not stated)"
    recom_model = recom.get("based_on_model") or "-"
    reasons = recom.get("reasons", [])
    backup_alt = recom.get("backup_alternative") or "(not stated)"
    backup_cond = recom.get("backup_condition") or "-"
    reasons_md = "\n".join(f"- {r}" for r in reasons) if isinstance(reasons, list) else str(reasons)

    banners = ""
    if unverified:
        banners += (
            "> ⚠️ **Data integrity warning:** the analysis contains decimal numbers that were not found in the "
            f"system calculations: `{', '.join(unverified)}`. Please check them against the results.\n\n"
        )
    for n in notes or []:
        banners += f"> ℹ️ {n}\n\n"

    def sec(key: str) -> str:
        return sections.get(key) or "_(this section is not available)_"

    return f"""# 📑 GDSS Decision Analysis Report

{banners}*AI engine:* `{model_used}`

---

## 1. 📋 Executive Summary & Group Consensus
{sec("ringkasan")}

---

## 2. ⚖️ Comparison Across Decision Methods
{sec("perbandingan")}

---

## 3. 📊 Strengths & Weaknesses of Each Method on This Case
{sec("kelebihan_kelemahan")}

---

## 4. 🎯 Final Recommendation
> ### 🏆 Main recommendation: **{recom_alt}**
> **Basis:** *{recom_model}*

**Key supporting reasons:**
{reasons_md}

**Backup alternative:**
- **Choice:** **{backup_alt}**
- **When to use it:** {backup_cond}

---

## 5. ⚠️ Risks & Change Scenarios
{sec("risiko")}

---

## 6. 📐 Integrity & Consistency of the Judgements (AHP)
{sec("konsistensi")}
"""


SECTION_LABELS = {
    "ringkasan": "Summary",
    "perbandingan": "Across methods",
    "kelebihan_kelemahan": "Strengths and weaknesses",
    "rekomendasi": "Recommendation",
    "risiko": "Risks",
    "konsistensi": "Consistency",
}

# Tokens for the visible answer; Gemini adds its own thinking room (see llm/client.py).
ANALYSIS_MAX_TOKENS = 6000


def _load_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "analysis_system.md"
    text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    first_fence, last_fence = text.find("```"), text.rfind("```")
    if first_fence != -1 and last_fence > first_fence:
        text = text[first_fence + 3:last_fence].strip()
    return text


def run_analysis(
    payload: Dict[str, Any],
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    keys: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    LLM analysis whose result is guaranteed complete (six sections) and uniform for any model.
    One request per report (the free tiers are small): if the selected engine fails, the next engine in the
    chain answers (see llm.client.build_chain); sections the model left weak are filled from the calculations.
    """
    messages = [
        {"role": "system", "content": _load_system_prompt()},
        {"role": "user", "content": "Here are the calculation results (JSON):\n" + json.dumps(payload, indent=2, ensure_ascii=False)},
    ]

    attempts: List[str] = []
    content, model_used = call_llm(
        messages=messages, provider=provider, model=model, temperature=0.2,
        max_tokens=ANALYSIS_MAX_TOKENS, api_key=api_key, json_mode=True,
        keys=keys, attempts=attempts,
    )
    if not content:
        error = " ".join(f"{i}) {m}" for i, m in enumerate(attempts, 1)) if len(attempts) > 1 else (model_used or "Unknown error.")
        return {
            "success": False,
            "error": error,
            "model_used": None,
            "attempts": attempts,
            "markdown": f"### Analysis failed\n\n{error}",
        }

    sections, report = complete_sections(robust_extract_sections(content, payload), payload)

    notes: List[str] = []
    if attempts:
        notes.append(
            "The selected engine could not answer, so the next one in line did. "
            + " ".join(attempts) + f" Answered by: {model_used}."
        )
    if report["fallback"]:
        notes.append(
            "These sections were written automatically from the calculation results because the model's answer for them "
            "was empty or incomplete: " + ", ".join(SECTION_LABELS[k] for k in report["fallback"]) + "."
        )

    unverified_numbers = validate_numbers_in_text(content, extract_all_numbers_from_json(payload))
    markdown_output = generate_markdown_from_sections(sections, model_used, unverified_numbers, notes)

    return {
        "success": True,
        "run_id": payload.get("run_id"),
        "model_used": model_used,
        "sections": sections,
        "markdown": markdown_output,
        "unverified_numbers": unverified_numbers,
        "completeness": report,
        "attempts": attempts,
        "notes": notes,
    }
