"""
Summaries derived from RunResult for the business team.
No new model calculations here: it only reads scores and ranks the engine already produced.
"""
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from engine.ranking import detect_close_calls
from engine.schemas import RunResult, Session
from app.labels import GROUP_ORDER


def session_fingerprint(session: Session) -> str:
    """Fingerprint of the data that affects the calculation (title and goal deliberately excluded)."""
    payload = {
        "alternatives": [a.model_dump() for a in session.alternatives],
        "criteria": [c.model_dump() for c in session.criteria],
        "values": session.values,
        "dms": [d.model_dump() for d in session.dms],
        "dm_weighting": session.dm_weighting.model_dump(),
        "dm_inputs": {k: v.model_dump() for k, v in session.dm_inputs.items()},
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def group_keys(result: RunResult) -> List[str]:
    """Keys of the group models present in the result, in a fixed display order."""
    ordered = [k for k in GROUP_ORDER if k in result.group]
    ordered += [k for k in result.group if k not in ordered]
    return ordered


def top_alts(ranks: Dict[str, int]) -> List[str]:
    return [a for a, r in ranks.items() if r == 1]


def rank_table(result: RunResult) -> pd.DataFrame:
    """Rows = alternatives, columns = group models, cells = ranks."""
    keys = group_keys(result)
    data = {k: pd.Series(result.group[k].ranks) for k in keys}
    return pd.DataFrame(data, index=result.alternatives)


def consensus(result: RunResult) -> Dict[str, Any]:
    """
    The alternative with the best average rank across all group models.
    Ties are broken by the number of wins, then by the alternatives' order in the data.
    """
    keys = group_keys(result)
    ranks = rank_table(result)
    avg = ranks.mean(axis=1)
    wins = pd.Series(
        {a: sum(1 for k in keys if a in top_alts(result.group[k].ranks)) for a in result.alternatives}
    )
    order_idx = {a: i for i, a in enumerate(result.alternatives)}
    table = pd.DataFrame({"avg_rank": avg, "wins": wins})
    table["_o"] = [order_idx[a] for a in table.index]
    table = table.sort_values(["avg_rank", "wins", "_o"], ascending=[True, False, True]).drop(columns="_o")
    best = table.index[0]
    agree = [k for k in keys if best in top_alts(result.group[k].ranks)]
    differ = [k for k in keys if k not in agree]
    return {
        "best": best,
        "table": table,
        "agree": agree,
        "differ": differ,
        "n_methods": len(keys),
    }


def dm_picks(result: RunResult, criteria_names: Dict[str, str]) -> List[Dict[str, Any]]:
    """For each DM: role, vote weight, most emphasised criteria, and the AHP winner (the mandatory method; this ranking is what feeds Borda and Copeland)."""
    rows = []
    for dm_id, indiv in result.individual.items():
        model = indiv.models.get(indiv.chosen_method) or next(iter(indiv.models.values()))
        weights = sorted(indiv.criteria_weights.items(), key=lambda kv: kv[1], reverse=True)
        rows.append(
            {
                "dm_id": dm_id,
                "role": indiv.role,
                "vote_weight": result.dm_weights.weights.get(dm_id, 0.0),
                "method": indiv.chosen_method,
                "winners": top_alts(model.ranks),
                "top_criteria": [(c, w) for c, w in weights[:2]],
                "cr": float(indiv.consistency.get("CR", 0.0)) if indiv.consistency else 0.0,
            }
        )
    return rows


def close_calls(result: RunResult) -> List[Dict[str, Any]]:
    """Very thin score gaps between consecutive ranks; `top` = involves rank 1."""
    out = []
    for key in group_keys(result):
        res = result.group[key]
        for cc in detect_close_calls(res.scores, res.ranks):
            out.append({"model": key, "top": cc["rank_a"] == 1, **cc})
    return out


def agreement_matrix(result: RunResult, kind: str = "spearman") -> Tuple[List[str], List[List[float]]]:
    """
    Correlation matrix between group models. The pipeline stores pairs under the key "A|B".
    Diagonal = 1, symmetric.
    """
    keys = group_keys(result)
    raw = (result.agreement or {}).get(kind, {}) or {}
    idx = {k: i for i, k in enumerate(keys)}
    n = len(keys)
    mat: List[List[Optional[float]]] = [[None] * n for _ in range(n)]
    for i in range(n):
        mat[i][i] = 1.0
    for pair, val in raw.items():
        if "|" not in pair:
            continue
        a, b = pair.split("|", 1)
        if a in idx and b in idx:
            mat[idx[a]][idx[b]] = val
            mat[idx[b]][idx[a]] = val
    return keys, mat
