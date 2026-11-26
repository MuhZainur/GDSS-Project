"""
Guarantees the AI report is complete and uniform, whichever model answers.

Flow: the model's answer is normalised (uniform shape) -> each section is scored -> any weak section is filled
from the calculation results (deterministic, nothing invented).

The five report views in the UI are served by these six sections:
  Summary                  <- ringkasan + rekomendasi
  Across methods           <- perbandingan
  Strengths and weaknesses <- kelebihan_kelemahan (table)
  Risks and consistency    <- risiko + konsistensi
  Full document            <- everything combined

The section keys are internal identifiers (the prompt asks models to use exactly these names).
"""
import re
from typing import Any, Dict, List, Optional, Tuple

from app.labels import GROUP_ORDER, group_label

SECTION_KEYS = ["ringkasan", "perbandingan", "kelebihan_kelemahan", "rekomendasi", "risiko", "konsistensi"]
TEXT_KEYS = ["ringkasan", "perbandingan", "kelebihan_kelemahan", "risiko", "konsistensi"]

MIN_CHARS = {"ringkasan": 150, "perbandingan": 200, "risiko": 150, "konsistensi": 100}
MIN_REASONS = 2
MAX_REASONS = 5

TABLE_HEADER = "| Model | Strengths on This Data | Weaknesses on This Data |\n|---|---|---|\n"

AUTO_NOTE = (
    "\n\n_This section was written automatically from the calculation results because the AI model's "
    "answer for it was empty or incomplete._"
)

# Traits of each group method (data-neutral; used for the fallback strengths/weaknesses table)
METHOD_TRAITS: Dict[str, Tuple[str, str]] = {
    "AHP_GROUP_AIP": (
        "Keeps the score gaps of each decision maker's preferences; weights come from pairwise comparisons.",
        "The result depends on how consistent each decision maker's judgements are (CR).",
    ),
    "SAW_GROUP": (
        "Simple and easy to explain; uses the raw value of every criterion.",
        "Fully compensatory: a very high value on one criterion can hide weaknesses on others; sensitive to outliers.",
    ),
    "TOPSIS_GROUP": (
        "Weighs the distance to the ideal solution and the distance from the worst solution together.",
        "Sensitive to changes in the set of alternatives (rank reversal).",
    ),
    "WP_GROUP": (
        "Multiplying with exponents limits the dominance of a single criterion and is fair to mixed units.",
        "Sensitive to very small values; score gaps between ranks can be thin.",
    ),
    "PROFILE_MATCHING_GROUP": (
        "Scores how close each alternative is to an ideal profile through per-criterion gaps.",
        "Does not distinguish how far a value exceeds the target; the gap conversion uses a fixed weight table.",
    ),
    "COPELAND_GROUP": (
        "Head-to-head contests make it robust against outlier values.",
        "Ignores the size of score gaps; can produce tied ranks.",
    ),
    "BORDA_WEIGHTED": (
        "Combines the rankings of all decision makers while respecting their vote weights.",
        "Uses only the order, not the size of score gaps; depends heavily on the vote weights.",
    ),
    "BORDA_UNWEIGHTED": (
        "Every decision maker gets one equal vote, which is easy for everyone to accept.",
        "Ignores differences in authority or influence between decision makers.",
    ),
}


# ── Data helpers ─────────────────────────────────────────────────────────────
def alt_names(payload: Dict[str, Any]) -> Dict[str, str]:
    return {a["id"]: a.get("name", a["id"]) for a in payload.get("alternatives", [])}


def alt_label(payload: Dict[str, Any], alt_id: str) -> str:
    names = alt_names(payload)
    return f"{alt_id} ({names[alt_id]})" if alt_id in names else str(alt_id)


def group_keys(payload: Dict[str, Any]) -> List[str]:
    groups = payload.get("group_rankings", {})
    return [k for k in GROUP_ORDER if k in groups] + [k for k in groups if k not in GROUP_ORDER]


def _top(ranks: Dict[str, int]) -> List[str]:
    return [a for a, r in ranks.items() if r == 1]


def consensus_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Average rank of each alternative across group methods; ties are broken by number of wins, then data order."""
    keys = group_keys(payload)
    ids = [a["id"] for a in payload.get("alternatives", [])]
    avg: Dict[str, float] = {}
    wins: Dict[str, int] = {}
    for a in ids:
        rs = [payload["group_rankings"][k]["ranks"].get(a) for k in keys]
        rs = [r for r in rs if r is not None]
        avg[a] = sum(rs) / len(rs) if rs else float(len(ids))
        wins[a] = sum(1 for k in keys if a in _top(payload["group_rankings"][k]["ranks"]))
    order = sorted(ids, key=lambda a: (avg[a], -wins[a], ids.index(a)))
    return {"order": order, "avg": avg, "wins": wins, "n_methods": len(keys), "keys": keys}


def match_alt(text: Any, payload: Dict[str, Any]) -> Optional[str]:
    """Find the alternative mentioned in a text (full id or name)."""
    if not isinstance(text, str) or not text.strip():
        return None
    names = alt_names(payload)
    for aid in names:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(aid)}(?![A-Za-z0-9])", text):
            return aid
    low = text.lower()
    for aid, nm in sorted(names.items(), key=lambda kv: -len(kv[1])):
        if nm and nm.lower() in low:
            return aid
    return None


def crit_standing(payload: Dict[str, Any], alt_id: str) -> List[Dict[str, Any]]:
    """Rank of an alternative's value on each criterion (benefit/cost direction respected)."""
    out = []
    alts = payload.get("alternatives", [])
    for c in payload.get("criteria", []):
        vals = {a["id"]: a.get("values", {}).get(c["id"]) for a in alts}
        vals = {k: v for k, v in vals.items() if isinstance(v, (int, float))}
        if alt_id not in vals:
            continue
        better_high = str(c.get("type", "benefit")).lower() == "benefit"
        ordered = sorted(vals.items(), key=lambda kv: kv[1], reverse=better_high)
        rank = [k for k, _ in ordered].index(alt_id) + 1
        out.append({"id": c["id"], "name": c.get("name", c["id"]), "unit": c.get("unit") or "", "value": vals[alt_id], "rank": rank, "n": len(vals)})
    return out


def _num(v: float) -> str:
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def _dm_ahp_winner(payload: Dict[str, Any], dm_id: str) -> Optional[str]:
    try:
        return _top(payload["individual_rankings"][dm_id]["AHP"]["ranks"])[0]
    except (KeyError, IndexError):
        return None


# ── Shape normalisation ──────────────────────────────────────────────────────
def _strip_heading(text: str) -> str:
    lines = text.strip().split("\n")
    while lines and (lines[0].lstrip().startswith("#") or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines).strip()


def coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _strip_heading(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(f"- {coerce_text(v)}" for v in value if coerce_text(v))
    if isinstance(value, dict):
        return "\n".join(f"- **{k}**: {coerce_text(v)}" for k, v in value.items() if coerce_text(v))
    return str(value)


def _pick(d: Dict[str, Any], *needles: str) -> Optional[str]:
    for k, v in d.items():
        if any(n in str(k).lower() for n in needles):
            return coerce_text(v).replace("\n", " ")
    return None


def coerce_table(value: Any) -> str:
    """Model | Strengths | Weaknesses table in markdown, from a string, a list of objects, or nested objects."""
    rows: List[Tuple[str, str, str]] = []
    pros, cons = ("strength", "pros", "advantage"), ("weakness", "cons", "weak")
    if isinstance(value, dict) and value and all(isinstance(v, dict) for v in value.values()):
        for name, d in value.items():
            rows.append((str(name), _pick(d, *pros) or "-", _pick(d, *cons) or "-"))
    elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
        for d in value:
            name = _pick(d, "model", "method", "name") or "-"
            rows.append((name, _pick(d, *pros) or "-", _pick(d, *cons) or "-"))
    if rows:
        body = "\n".join(f"| {a} | {b.replace('|', '/')} | {c.replace('|', '/')} |" for a, b, c in rows)
        return TABLE_HEADER + body
    return coerce_text(value)


def table_row_count(text: str) -> int:
    rows = [l for l in text.split("\n") if l.strip().startswith("|")]
    data = [l for l in rows if not re.fullmatch(r"\|?[\s:\-|]+\|?", l.strip())]
    return max(0, len(data) - 1)  # minus the header row


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", p).strip() for p in value.split("\n")]
        return [p for p in parts if p]
    if isinstance(value, list):
        return [coerce_text(v).replace("\n", " ") for v in value if coerce_text(v)]
    return [coerce_text(value)]


def normalize_recommendation(rec: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(rec, str):
        rec = {"alternative": rec}
    if not isinstance(rec, dict):
        rec = {}
    out: Dict[str, Any] = {}
    main = match_alt(coerce_text(rec.get("alternative")), payload)
    backup = match_alt(coerce_text(rec.get("backup_alternative")), payload)
    out["alternative"] = alt_label(payload, main) if main else ""
    out["backup_alternative"] = alt_label(payload, backup) if backup and backup != main else ""
    out["based_on_model"] = coerce_text(rec.get("based_on_model")).replace("\n", " ")
    reasons: List[str] = []
    for r in _as_list(rec.get("reasons")):
        if r not in reasons:
            reasons.append(r)
    out["reasons"] = reasons[:MAX_REASONS]
    out["backup_condition"] = coerce_text(rec.get("backup_condition")).replace("\n", " ")
    return out


def normalize_sections(sections: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in ["ringkasan", "perbandingan", "risiko", "konsistensi"]:
        if k in sections:
            out[k] = coerce_text(sections[k])
    if "kelebihan_kelemahan" in sections:
        out["kelebihan_kelemahan"] = coerce_table(sections["kelebihan_kelemahan"])
    if "rekomendasi" in sections:
        out["rekomendasi"] = normalize_recommendation(sections["rekomendasi"], payload)
    return out


# ── Completeness scoring ─────────────────────────────────────────────────────
def assess(sections: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, str]:
    """Weak section key -> reason. Empty when every section meets the requirements."""
    weak: Dict[str, str] = {}
    cons = consensus_from_payload(payload)
    method_words = ["Borda", "Copeland", "AHP", "SAW", "WP", "TOPSIS", "Profile"]

    def text(k: str) -> str:
        v = sections.get(k)
        return v if isinstance(v, str) else ""

    for k in ["ringkasan", "perbandingan", "risiko", "konsistensi"]:
        t = text(k)
        if len(t) < MIN_CHARS[k]:
            weak[k] = f"empty or too short (at least {MIN_CHARS[k]} characters)"
    if "ringkasan" not in weak and not match_alt(text("ringkasan"), payload):
        weak["ringkasan"] = "does not name any alternative"
    if "perbandingan" not in weak and sum(1 for w in method_words if w.lower() in text("perbandingan").lower()) < 2:
        weak["perbandingan"] = "does not compare at least two methods"
    if "konsistensi" not in weak and not re.search(r"CR|consisten", text("konsistensi"), re.I):
        weak["konsistensi"] = "does not discuss the consistency ratio (CR)"

    need = min(5, max(2, cons["n_methods"]))
    if table_row_count(text("kelebihan_kelemahan")) < need:
        weak["kelebihan_kelemahan"] = f"the table needs at least {need} method rows"

    rec = sections.get("rekomendasi")
    if not isinstance(rec, dict) or not rec.get("alternative"):
        weak["rekomendasi"] = "main alternative is missing or not recognised"
    elif not rec.get("backup_alternative"):
        weak["rekomendasi"] = "backup alternative is missing or equals the main one"
    elif len(rec.get("reasons", [])) < MIN_REASONS:
        weak["rekomendasi"] = f"fewer than {MIN_REASONS} reasons"
    elif len(rec.get("backup_condition", "")) < 15:
        weak["rekomendasi"] = "backup condition is empty"
    return weak


# ── Fallback content from the calculation results ────────────────────────────
def fallback_reasons(payload: Dict[str, Any], alt_id: str) -> List[str]:
    cons = consensus_from_payload(payload)
    reasons = [
        f"Ranked first in {cons['wins'][alt_id]} of {cons['n_methods']} group methods, "
        f"with an average rank of {cons['avg'][alt_id]:.2f} (position {cons['order'].index(alt_id) + 1} of {len(cons['order'])})."
    ]
    standing = sorted(crit_standing(payload, alt_id), key=lambda s: s["rank"])
    best = [s for s in standing if s["rank"] == 1][:2] or standing[:1]
    if best:
        reasons.append(
            "Leads on " + "; ".join(f"{s['name']} (value {_num(s['value'])} {s['unit']}".rstrip() + f", rank {s['rank']} of {s['n']})" for s in best) + "."
        )
    agree_dm = [d["role"] for d in payload.get("dm", []) if _dm_ahp_winner(payload, d["id"]) == alt_id]
    if agree_dm:
        reasons.append("Chosen by AHP for: " + ", ".join(agree_dm) + ".")
    return reasons[:MAX_REASONS]


def fallback_backup_condition(payload: Dict[str, Any], main: str, backup: str) -> str:
    roles = [d["role"] for d in payload.get("dm", []) if _dm_ahp_winner(payload, d["id"]) == backup]
    if roles:
        return f"If the votes of {', '.join(roles)} are given more weight, since they are the ones backing {alt_label(payload, backup)}."
    return f"If priorities shift towards the strengths of {alt_label(payload, backup)} or {alt_label(payload, main)} runs into obstacles."


def fallback_recommendation(payload: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Completes the recommendation: valid parts from the model are kept, the rest is derived from the data."""
    existing = existing or {}
    cons = consensus_from_payload(payload)
    main_label = existing.get("alternative") or alt_label(payload, cons["order"][0])
    main_id = match_alt(main_label, payload) or cons["order"][0]
    backup_label = existing.get("backup_alternative")
    backup_id = match_alt(backup_label, payload) if backup_label else None
    if not backup_id or backup_id == main_id:
        backup_id = next(a for a in cons["order"] if a != main_id)
    reasons = list(existing.get("reasons", []))
    if len(reasons) < MIN_REASONS:
        reasons = (reasons + [r for r in fallback_reasons(payload, main_id) if r not in reasons])[:MAX_REASONS]
    cond = existing.get("backup_condition", "")
    if len(cond) < 15:
        cond = fallback_backup_condition(payload, main_id, backup_id)
    return {
        "alternative": alt_label(payload, main_id),
        "based_on_model": existing.get("based_on_model") or "Average rank across all group methods",
        "reasons": reasons,
        "backup_alternative": alt_label(payload, backup_id),
        "backup_condition": cond,
    }


def _close_calls(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(payload.get("flags", {}).get("close_calls", []))


def _winners(payload: Dict[str, Any], key: str) -> str:
    return ", ".join(alt_label(payload, a) for a in _top(payload["group_rankings"][key]["ranks"]))


def fallback_text(key: str, payload: Dict[str, Any]) -> str:
    cons = consensus_from_payload(payload)
    keys = cons["keys"]
    groups = payload["group_rankings"]
    best = cons["order"][0]
    best_lab = alt_label(payload, best)

    if key == "ringkasan":
        differ = [k for k in keys if best not in _top(groups[k]["ranks"])]
        s = (
            f"The group recommendation is **{best_lab}**: ranked first in {cons['wins'][best]} of {cons['n_methods']} group methods, "
            f"with an average rank of {cons['avg'][best]:.2f}."
        )
        if len(cons["order"]) > 1:
            second = cons["order"][1]
            s += f" Next is {alt_label(payload, second)} (average rank {cons['avg'][second]:.2f})."
        if differ:
            s += " Methods that prefer another alternative: " + "; ".join(
                f"{group_label(k)} picks {_winners(payload, k)}" for k in differ
            ) + "."
        else:
            s += " All group methods agree on this choice."
        dms = sorted(payload.get("dm", []), key=lambda d: d.get("weight", 0), reverse=True)
        if dms:
            s += f" The largest vote weight belongs to {dms[0]['role']} ({dms[0]['weight'] * 100:.0f}%)."
        if _close_calls(payload):
            s += f" There are {len(_close_calls(payload))} very thin score gaps between ranks, so some positions are sensitive to small changes in the data."
        return s

    if key == "perbandingan":
        lines = ["Winner of each group method:"]
        for k in keys:
            lines.append(f"- **{group_label(k)}**: {_winners(payload, k)}")
        agree = [group_label(k) for k in keys if best in _top(groups[k]["ranks"])]
        differ = [k for k in keys if best not in _top(groups[k]["ranks"])]
        lines.append("")
        lines.append(f"Methods that agree on {best_lab}: {', '.join(agree) if agree else 'none'}.")
        if differ:
            lines.append("Why some methods differ:")
            for k in differ:
                trait = METHOD_TRAITS.get(k, ("", ""))[1]
                lines.append(f"- {group_label(k)} picks {_winners(payload, k)}. {trait}")
        else:
            lines.append("No method disagrees, so the result holds up regardless of how it is calculated.")
        return "\n".join(lines)

    if key == "kelebihan_kelemahan":
        rows = []
        cc = _close_calls(payload)
        for k in keys:
            pro, con = METHOD_TRAITS.get(k, ("-", "-"))
            close = next((c for c in cc if c.get("model") == k), None)
            con_txt = con + (f" On this data the gap between {alt_label(payload, close['a'])} and {alt_label(payload, close['b'])} is very thin." if close else "")
            rows.append(f"| {group_label(k)} | {pro} Picks {_winners(payload, k)}. | {con_txt} |")
        return TABLE_HEADER + "\n".join(rows)

    if key == "risiko":
        lines = []
        for c in _close_calls(payload)[:4]:
            lines.append(f"- In {group_label(c['model'])}, {alt_label(payload, c['a'])} and {alt_label(payload, c['b'])} are almost level (score gap {c['gap']:.4f}); their order can flip if the data shifts slightly.")
        for t in payload.get("flags", {}).get("ties", [])[:3]:
            lines.append(f"- {group_label(t['model'])} gives a tie at rank {t['rank']} for " + ", ".join(alt_label(payload, a) for a in t["alternatives"]) + ".")
        weak = sorted(crit_standing(payload, best), key=lambda s: -s["rank"])[:2]
        for s in weak:
            if s["rank"] > 1:
                lines.append(f"- {best_lab} is weakest on {s['name']}: value {_num(s['value'])} {s['unit']}".rstrip() + f" (rank {s['rank']} of {s['n']}).")
        dms = sorted(payload.get("dm", []), key=lambda d: d.get("weight", 0), reverse=True)
        if dms:
            lines.append(f"- Rank-based methods (Borda, Copeland) are sensitive to vote weights; {dms[0]['role']} holds {dms[0]['weight'] * 100:.0f}%. Test weight changes on the Compare page (what-if).")
        against = [d["role"] for d in payload.get("dm", []) if _dm_ahp_winner(payload, d["id"]) not in (None, best)]
        if against:
            lines.append("- Decision makers who back another alternative under AHP: " + ", ".join(against) + ". Their support needs to be kept when the decision is carried out.")
        return "\n".join(lines) or "- No thin score gaps, tied ranks or notable disagreement were found in the calculation results."

    if key == "konsistensi":
        dms = payload.get("dm", [])
        rows = "\n".join(
            f"| {d['role']} | {d.get('CR', 0):.4f} | {'Consistent' if d.get('CR', 0) < 0.1 else 'Needs revision'} |" for d in dms
        )
        bad = [d["role"] for d in dms if d.get("CR", 0) >= 0.1]
        verdict = (
            "Every decision maker has a consistency ratio (CR) below the 0.1 limit, so the criteria weights can be trusted."
            if not bad else
            "CR is above the 0.1 limit for: " + ", ".join(bad) + ". Their judgements should be reviewed before the result is used."
        )
        return f"{verdict}\n\n| Decision maker | CR | Status |\n|---|---|---|\n{rows}"

    return ""


# ── Final completion ─────────────────────────────────────────────────────────
def complete_sections(sections: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Returns (complete sections, report). Report: weak (sections that failed the check) and fallback
    (sections filled from the calculation results). All six sections are guaranteed to exist and to pass `assess`.
    """
    sections = normalize_sections(sections, payload)
    weak = assess(sections, payload)
    for k in weak:
        if k == "rekomendasi":
            sections[k] = fallback_recommendation(payload, sections.get(k) if isinstance(sections.get(k), dict) else None)
        else:
            sections[k] = fallback_text(k, payload) + AUTO_NOTE
    return sections, {"weak": list(weak), "fallback": list(weak)}
