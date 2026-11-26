"""
Editing the structure of a case: add/remove products, criteria and decision makers (DMs),
while keeping all derived data aligned (values, each DM's assessment, vote weights).

This module is pure (no Streamlit) so it is easy to test. The calculation engine is unchanged:
every function only produces a `Session` that is valid for `engine.pipeline.run_all`.
"""
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from engine.schemas import Alternative, Criterion, DM, DMInput, DMWeighting, Session

MIN_ALTERNATIVES, MAX_ALTERNATIVES = 3, 12
MIN_CRITERIA, MAX_CRITERIA = 3, 10
MIN_DMS, MAX_DMS = 2, 10

CRITERION_TYPES = ("benefit", "cost")


# ── Small helpers ───────────────────────────────────────────────────────────
def id_number(identifier: str) -> int:
    digits = re.sub(r"\D", "", str(identifier))
    return int(digits) if digits else 0


def id_sort_key(identifier: str) -> Tuple[str, int]:
    """Natural order: C2 before C10."""
    return (re.sub(r"\d", "", str(identifier)), id_number(identifier))


def next_id(prefix: str, existing: List[str]) -> str:
    return f"{prefix}{max([id_number(i) for i in existing] + [0]) + 1}"


def _unique_name(base: str, taken: List[str]) -> str:
    low = {t.strip().lower() for t in taken}
    n = len(taken) + 1
    while f"{base} {n}".lower() in low:
        n += 1
    return f"{base} {n}"


def as_float(v: Any) -> float:
    if isinstance(v, str) and "/" in v:
        a, b = v.split("/", 1)
        return float(a) / float(b)
    return float(v)


def reciprocal(v: Any) -> Any:
    """Reciprocal of a Saaty-scale value with the same encoding as the slider: 3 <-> '1/3', 1 <-> 1."""
    try:
        x = as_float(v)
    except (ValueError, ZeroDivisionError, TypeError):
        return 1
    if x <= 0:
        return 1
    if abs(x - 1) < 1e-9:
        return 1
    if x > 1:
        r = round(x)
        return f"1/{r}" if abs(x - r) < 1e-9 else 1.0 / x
    k = 1.0 / x
    r = round(k)
    return r if abs(k - r) < 1e-9 else k


def saved_pair(pairwise: Optional[List[List[Any]]], order: Optional[List[str]], a: str, b: str) -> Any:
    """Stored comparison value of 'a vs b'; 1 when the pair was never assessed."""
    if not pairwise or not order or a not in order or b not in order:
        return 1
    i, j = order.index(a), order.index(b)
    try:
        return pairwise[i][j]
    except (IndexError, TypeError):
        return 1


def build_pairwise(ids: List[str], old_pairwise: Optional[List[List[Any]]], old_order: Optional[List[str]]) -> List[List[Any]]:
    """Pairwise matrix for `ids`; old judgements are kept per pair, new pairs = 1 (equally important)."""
    n = len(ids)
    m: List[List[Any]] = [[1] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            v = saved_pair(old_pairwise, old_order, ids[i], ids[j])
            m[i][j] = v
            m[j][i] = reciprocal(v)
    return m


# ── Synchronisation ─────────────────────────────────────────────────────────────
def sync_session(s: Session) -> Session:
    """
    Aligns all derived data with the current lists of products, criteria and DMs:
    - the value table covers every product x criterion (new cell = 0, stale cells dropped);
    - every DM assesses ALL criteria (old judgements are kept per pair);
    - DM vote weights follow the DM list; each DM's reference method is always AHP.
    """
    s = s.model_copy(deep=True)
    alt_ids = [a.id for a in s.alternatives]
    crit_ids = [c.id for c in s.criteria]
    dm_ids = [d.id for d in s.dms]

    s.values = {
        a: {c: float(s.values.get(a, {}).get(c, 0.0)) for c in crit_ids}
        for a in alt_ids
    }

    new_inputs: Dict[str, DMInput] = {}
    for dm in dm_ids:
        old = s.dm_inputs.get(dm)
        pw = build_pairwise(crit_ids, old.pairwise if old else None, old.criteria if old else None)
        new_inputs[dm] = DMInput(
            criteria=list(crit_ids),
            pairwise=pw,
            chosen_method="AHP",
            submitted_at=old.submitted_at if old else None,
        )
    s.dm_inputs = new_inputs

    old_w = s.dm_weighting
    old_order = old_w.order or None
    s.dm_weighting = DMWeighting(
        mode=old_w.mode if old_w.mode in ("ahp", "equal") else "equal",
        pairwise=build_pairwise(dm_ids, old_w.pairwise, old_order or dm_ids),
        order=list(dm_ids),
    )
    return s


# ── Add / remove ───────────────────────────────────────────────────────────
def add_alternative(s: Session) -> Session:
    if len(s.alternatives) >= MAX_ALTERNATIVES:
        return s
    s = s.model_copy(deep=True)
    ids = [a.id for a in s.alternatives]
    s.alternatives.append(Alternative(id=next_id("A", ids), name=_unique_name("Product", [a.name for a in s.alternatives])))
    return sync_session(s)


def remove_alternative(s: Session, alt_id: str) -> Session:
    if len(s.alternatives) <= MIN_ALTERNATIVES or alt_id not in {a.id for a in s.alternatives}:
        return s
    s = s.model_copy(deep=True)
    s.alternatives = [a for a in s.alternatives if a.id != alt_id]
    return sync_session(s)


def add_criterion(s: Session) -> Session:
    if len(s.criteria) >= MAX_CRITERIA:
        return s
    s = s.model_copy(deep=True)
    ids = [c.id for c in s.criteria]
    s.criteria.append(Criterion(id=next_id("C", ids), name=_unique_name("Criterion", [c.name for c in s.criteria]), type="benefit"))
    return sync_session(s)


def remove_criterion(s: Session, crit_id: str) -> Session:
    if len(s.criteria) <= MIN_CRITERIA or crit_id not in {c.id for c in s.criteria}:
        return s
    s = s.model_copy(deep=True)
    s.criteria = [c for c in s.criteria if c.id != crit_id]
    return sync_session(s)


def add_dm(s: Session) -> Session:
    if len(s.dms) >= MAX_DMS:
        return s
    s = s.model_copy(deep=True)
    ids = [d.id for d in s.dms]
    s.dms.append(DM(id=next_id("DM", ids), role=_unique_name("Decision maker", [d.role for d in s.dms])))
    return sync_session(s)


def remove_dm(s: Session, dm_id: str) -> Session:
    if len(s.dms) <= MIN_DMS or dm_id not in {d.id for d in s.dms}:
        return s
    s = s.model_copy(deep=True)
    s.dms = [d for d in s.dms if d.id != dm_id]
    return sync_session(s)


# ── Value table ──────────────────────────────────────────────────────────────
def apply_value_table(s: Session, table: Dict[str, Dict[str, Any]]) -> Session:
    """
    Applies an edited value table {alt_id: {crit_id: value}}.
    Empty or non-numeric cells are silently ignored (the old value is kept) so the session cannot break.
    """
    values = {a.id: dict(s.values.get(a.id, {})) for a in s.alternatives}
    for a in s.alternatives:
        for c in s.criteria:
            raw = table.get(a.id, {}).get(c.id)
            try:
                v = float(raw)
            except (TypeError, ValueError):
                continue
            if math.isfinite(v):
                values[a.id][c.id] = v
    return s.model_copy(update={"values": values})


# ── Empty case ─────────────────────────────────────────────────────────────
def blank_session() -> Session:
    s = Session(
        session_id="new-case",
        title="New decision case",
        goal="Write the decision goal here",
        company="",
        data_note=None,
        alternatives=[Alternative(id=f"A{i}", name=f"Product {i}") for i in range(1, 4)],
        criteria=[Criterion(id=f"C{i}", name=f"Criterion {i}", type="benefit") for i in range(1, 4)],
        values={},
        dms=[DM(id=f"DM{i}", role=f"Decision maker {i}") for i in range(1, 3)],
        dm_weighting=DMWeighting(mode="equal"),
        dm_inputs={},
    )
    return sync_session(s)


# ── Validation ──────────────────────────────────────────────────────────────
def validate_case(s: Session) -> List[Tuple[str, str]]:
    """
    List of data problems: [("bad", text)] blocks the analysis, [("warn", text)] is only a warning.
    """
    out: List[Tuple[str, str]] = []

    if len(s.alternatives) < MIN_ALTERNATIVES:
        out.append(("bad", f"At least {MIN_ALTERNATIVES} candidate products are needed (currently {len(s.alternatives)})."))
    if len(s.criteria) < MIN_CRITERIA:
        out.append(("bad", f"At least {MIN_CRITERIA} criteria are needed (currently {len(s.criteria)})."))
    if len(s.dms) < MIN_DMS:
        out.append(("bad", f"At least {MIN_DMS} decision makers are needed for a group decision (currently {len(s.dms)})."))

    def _check_names(items: List[Tuple[str, str]], noun: str) -> None:
        seen: Dict[str, str] = {}
        for ident, name in items:
            nm = (name or "").strip()
            if not nm:
                out.append(("bad", f"Name of {noun} {ident} is still empty."))
                continue
            key = nm.lower()
            if key in seen:
                out.append(("bad", f"The {noun} name \"{nm}\" is used twice ({seen[key]} and {ident}). Give them different names."))
            else:
                seen[key] = ident

    _check_names([(a.id, a.name) for a in s.alternatives], "product")
    _check_names([(c.id, c.name) for c in s.criteria], "criterion")
    _check_names([(d.id, d.role) for d in s.dms], "role")

    for c in s.criteria:
        if c.type.lower() not in CRITERION_TYPES:
            out.append(("bad", f"The type of criterion {c.name or c.id} must be Benefit or Cost."))

    zero_cells: List[str] = []
    for c in s.criteria:
        is_cost = c.type.lower() == "cost"
        col: List[float] = []
        for a in s.alternatives:
            v = s.values.get(a.id, {}).get(c.id)
            if v is None or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
                out.append(("bad", f"The value of {a.name or a.id} on {c.name or c.id} is not a number yet."))
                continue
            v = float(v)
            col.append(v)
            if v < 0:
                out.append(("bad", f"The value of {a.name or a.id} on {c.name or c.id} is negative; use 0 or more."))
            elif v == 0 and is_cost:
                out.append(("bad", f"The value of {a.name or a.id} on {c.name or c.id} (Cost) cannot be 0 because it is used as a divisor."))
            elif v == 0:
                zero_cells.append(f"{a.name or a.id} / {c.name or c.id}")
        if col and not is_cost and max(col) <= 0:
            out.append(("bad", f"All values of criterion {c.name or c.id} are 0. Enter at least one positive number."))
    if zero_cells:
        shown = "; ".join(zero_cells[:4]) + ("…" if len(zero_cells) > 4 else "")
        out.append(("warn", f"{len(zero_cells)} value cells are still 0 ({shown}). Make sure they are really 0 and not just unfilled."))

    return out


def blocking_problems(s: Session) -> List[str]:
    return [t for k, t in validate_case(s) if k == "bad"]
