from typing import Dict, Any, List
from engine.schemas import Session, RunResult
from engine.ranking import detect_close_calls

METHOD_NOTES = {
    "AHP": "Derives weights from consistent pairwise ratios; sensitive to the consistency of judgements (CR < 0.1).",
    "SAW": "Simple linear weighted sum; fully compensatory and sensitive to outliers.",
    "WP": "Weighted product with exponents; limits extreme compensation through the powers of benefit/cost weights.",
    "TOPSIS": "Picks the alternative closest to the ideal and farthest from the anti-ideal; sensitive to rank reversal.",
    "COPELAND": "Head-to-head contests (Condorcet tournament); rewards direct wins but ignores the size of score gaps.",
    "BORDA": "Rank-based consensus voting; gives ordered points to each decision maker's preference positions.",
    "AHP_AIP": "Aggregation of individual priorities with a weighted geometric mean; keeps the accuracy of preference score gaps."
}

def build_llm_payload(session: Session, result: RunResult) -> Dict[str, Any]:
    """Builds a compact payload (without step traces) to send to the LLM."""
    # Alternatives with values
    alts_data = []
    for a in session.alternatives:
        alts_data.append({
            "id": a.id,
            "name": a.name,
            "segment": a.segment,
            "values": session.values.get(a.id, {})
        })

    # Criteria
    crits_data = [
        {"id": c.id, "name": c.name, "unit": c.unit, "type": c.type}
        for c in session.criteria
    ]

    # DM data
    dm_data = []
    for d in session.dms:
        indiv = result.individual.get(d.id)
        dm_data.append({
            "id": d.id,
            "role": d.role,
            "weight": round(result.dm_weights.weights.get(d.id, 0.0), 4),
            "criteria_weights": {c: round(w, 4) for c, w in indiv.criteria_weights.items()} if indiv else {},
            "CR": round(indiv.consistency.get("CR", 0.0), 4) if indiv else 0.0,
            "chosen_method": indiv.chosen_method if indiv else "AHP"
        })

    # Individual rankings
    indiv_rankings = {}
    for dm_id, indiv in result.individual.items():
        indiv_rankings[dm_id] = {}
        for m_name, m_res in indiv.models.items():
            indiv_rankings[dm_id][m_name] = {
                "scores": {a: round(s, 4) for a, s in m_res.scores.items()},
                "ranks": m_res.ranks
            }

    # Group rankings
    group_rankings = {}
    for g_name, g_res in result.group.items():
        group_rankings[g_name] = {
            "scores": {a: round(s, 4) for a, s in g_res.scores.items()},
            "ranks": g_res.ranks
        }

    # Flags: inconsistent DMs, ties, close calls
    inconsistent_dm = [
        d["id"] for d in dm_data if d["CR"] >= 0.1
    ]

    ties = []
    for g_name, g_res in result.group.items():
        # find duplicate ranks
        rank_counts: Dict[int, List[str]] = {}
        for a, r in g_res.ranks.items():
            rank_counts.setdefault(r, []).append(a)
        for r, alts in rank_counts.items():
            if len(alts) > 1:
                ties.append({
                    "model": g_name,
                    "rank": r,
                    "alternatives": alts
                })

    close_calls = []
    for g_name, g_res in result.group.items():
        cc = detect_close_calls(g_res.scores, g_res.ranks)
        for c in cc:
            close_calls.append({
                "model": g_name,
                "a": c["a"],
                "b": c["b"],
                "gap": c["gap"]
            })

    flags = {
        "inconsistent_dm": inconsistent_dm,
        "ties": ties,
        "close_calls": close_calls
    }

    return {
        "run_id": result.run_id,
        "decision": {
            "goal": session.goal,
            "title": session.title,
            "company": session.company or ""
        },
        "alternatives": alts_data,
        "criteria": crits_data,
        "dm": dm_data,
        "individual_rankings": indiv_rankings,
        "group_rankings": group_rankings,
        "winners": result.winners,
        "agreement": result.agreement,
        "flags": flags,
        "method_notes": METHOD_NOTES
    }
