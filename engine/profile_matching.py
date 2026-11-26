"""
Profile Matching Engine
Based on the Intelligent DSS course material (Dr. Sri Mulyana, M. Kom - UGM)
Steps:
1. Map real values to the standard level scale (1 - 5)
2. Determine the target (ideal) profile
3. Compute GAP = Alternative Value - Target Value
4. Weight the GAP using the standard table (UGM / Kemenpan)
5. Group and compute the Core Factor (CF 60%) and Secondary Factor (SF 40%)
6. Compute the final total score and ranking
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

from engine.schemas import (
    Step,
    TableData,
    MatrixData,
    ResultBox,
    ModelResult
)
from engine.ranking import rank_min

# Standard GAP weight table (Dr. Sri Mulyana, M. Kom - UGM Slide 26)
GAP_WEIGHT_MAP = {
    0: 5.0,   # No difference (on target)
    1: 4.5,   # Surplus of 1 level(s)
    -1: 4.0,  # Shortfall of 1 level(s)
    2: 3.5,   # Surplus of 2 level(s)
    -2: 3.0,  # Shortfall of 2 level(s)
    3: 2.5,   # Surplus of 3 level(s)
    -3: 2.0,  # Shortfall of 3 level(s)
    4: 1.5,   # Surplus of 4 level(s)
    -4: 1.0,  # Shortfall of 4 level(s)
}

def map_gap_to_weight(gap: int) -> float:
    if gap in GAP_WEIGHT_MAP:
        return GAP_WEIGHT_MAP[gap]
    if gap > 4:
        return 1.5
    return 1.0

def scale_raw_to_likert(
    raw_val: float,
    min_val: float,
    max_val: float,
    is_benefit: bool
) -> int:
    """Converts a real value to the 1 - 5 scale."""
    if max_val <= min_val:
        return 3
    if is_benefit:
        ratio = (raw_val - min_val) / (max_val - min_val)
    else:
        ratio = (max_val - raw_val) / (max_val - min_val)
    val = 1 + int(round(ratio * 4.0))
    return max(1, min(5, val))

def solve_profile_matching_individual(
    dm_id: str,
    criteria: List[str],
    criteria_weights: np.ndarray,
    alternatives: List[str],
    criteria_types: Dict[str, str],
    values: Dict[str, Dict[str, float]],
    target_levels: Optional[Dict[str, int]] = None,
    core_factors: Optional[List[str]] = None,
    cf_weight: float = 0.6,
    sf_weight: float = 0.4
) -> ModelResult:
    """
    Solves Profile Matching for one Decision Maker (DM).
    The criteria weights (criteria_weights) come from that DM's AHP calculation.
    """
    steps: List[Step] = []
    num_alts = len(alternatives)
    num_crits = len(criteria)

    # 1. Determine the Min and Max value of each criterion
    crit_min_max = {}
    for c in criteria:
        vals = [values.get(a, {}).get(c, 0.0) for a in alternatives]
        crit_min_max[c] = (min(vals), max(vals))

    # 2. Map values to the 1 - 5 scale (rating)
    rating_matrix: Dict[str, Dict[str, int]] = {a: {} for a in alternatives}
    for a in alternatives:
        for c in criteria:
            raw = values.get(a, {}).get(c, 0.0)
            mn, mx = crit_min_max[c]
            is_ben = criteria_types.get(c, "benefit").lower() == "benefit"
            rating_matrix[a][c] = scale_raw_to_likert(raw, mn, mx, is_ben)

    # Step 1: 1 - 5 scale conversion table
    step1_rows = []
    for a in alternatives:
        row = [a]
        for c in criteria:
            raw = values.get(a, {}).get(c, 0.0)
            rate = rating_matrix[a][c]
            row.append(f"{rate} ({raw:g})")
        step1_rows.append(row)

    steps.append(Step(
        id="pm.scale",
        title="Step 1. Mapping Real Values to the Standard Level Scale (1 - 5)",
        explanation="Each criterion value is converted to a scale of 1 to 5 (Benefit: higher value, higher score; Cost: lower value, higher score).",
        table=TableData(
            columns=["Alternative"] + criteria,
            rows=step1_rows
        )
    ))

    # 3. Tentukan Target Profile
    if target_levels is None:
        # Default target level 5 (ideal/maximum) for all criteria
        target_levels = {c: 5 for c in criteria}

    # 4. Compute GAP = Value - Target
    gap_matrix: Dict[str, Dict[str, int]] = {a: {} for a in alternatives}
    for a in alternatives:
        for c in criteria:
            gap_matrix[a][c] = rating_matrix[a][c] - target_levels[c]

    step2_rows = [["Target Profile (Ideal)"] + [str(target_levels[c]) for c in criteria]]
    for a in alternatives:
        row = [a]
        for c in criteria:
            gap = gap_matrix[a][c]
            row.append(f"{gap:+d}")
        step2_rows.append(row)

    steps.append(Step(
        id="pm.gap",
        title="Step 2. GAP Calculation (Alternative Value - Target Value)",
        explanation="GAP is the alternative's rating minus the expected target profile value.",
        table=TableData(
            columns=["Alternative / Target"] + criteria,
            rows=step2_rows
        )
    ))

    # 5. Weight the GAP values
    gap_weight_matrix: Dict[str, Dict[str, float]] = {a: {} for a in alternatives}
    for a in alternatives:
        for c in criteria:
            gap_weight_matrix[a][c] = map_gap_to_weight(gap_matrix[a][c])

    step3_rows = []
    for a in alternatives:
        row = [a]
        for c in criteria:
            gw = gap_weight_matrix[a][c]
            row.append(f"{gw:.1f}")
        step3_rows.append(row)

    steps.append(Step(
        id="pm.gap_weights",
        title="Step 3. GAP Weighting Using the UGM Standard Table",
        explanation="The GAP is converted to a value weight: GAP 0 = 5.0, GAP 1 = 4.5, GAP -1 = 4.0, GAP 2 = 3.5, GAP -2 = 3.0, GAP 3 = 2.5, GAP -3 = 2.0, GAP 4 = 1.5, GAP -4 = 1.0.",
        table=TableData(
            columns=["Alternative"] + criteria,
            rows=step3_rows
        )
    ))

    # 6. Determine the Core Factor (CF) and Secondary Factor (SF)
    # If not set explicitly, use the criteria with the largest AHP weights (top ~40-50%) or C1, C2, C5
    if core_factors is None:
        # Find the criteria with an AHP weight above average (1/n)
        crit_w_dict = {c: criteria_weights[j] for j, c in enumerate(criteria)}
        avg_w = 1.0 / len(criteria)
        core_factors = [c for c in criteria if crit_w_dict.get(c, 0) >= avg_w]
        if not core_factors or len(core_factors) == len(criteria):
            # Take the default main technical criteria
            default_cf = ["C1", "C2", "C5"]
            core_factors = [c for c in default_cf if c in criteria]
            if not core_factors:
                core_factors = criteria[:max(1, len(criteria) // 2)]

    secondary_factors = [c for c in criteria if c not in core_factors]
    if not secondary_factors:
        secondary_factors = [core_factors.pop()]

    # 7. Compute NCF, NSF and the final total score
    ncf_scores: Dict[str, float] = {}
    nsf_scores: Dict[str, float] = {}
    total_scores: Dict[str, float] = {}
    ahp_weighted_scores: Dict[str, float] = {}

    crit_w_dict = {c: float(criteria_weights[j]) for j, c in enumerate(criteria)}

    step4_rows = []
    for a in alternatives:
        cf_vals = [gap_weight_matrix[a][c] for c in core_factors]
        sf_vals = [gap_weight_matrix[a][c] for c in secondary_factors]

        ncf = sum(cf_vals) / len(cf_vals) if cf_vals else 0.0
        nsf = sum(sf_vals) / len(sf_vals) if sf_vals else 0.0
        tot = (cf_weight * ncf) + (sf_weight * nsf)

        # AHP-weighted Profile Matching score
        ahp_tot = sum(crit_w_dict[c] * gap_weight_matrix[a][c] for c in criteria)

        ncf_scores[a] = ncf
        nsf_scores[a] = nsf
        total_scores[a] = float(tot)
        ahp_weighted_scores[a] = float(ahp_tot)

        step4_rows.append([
            a,
            f"{ncf:.4f}",
            f"{nsf:.4f}",
            f"({cf_weight*100:.0f}% × {ncf:.2f}) + ({sf_weight*100:.0f}% × {nsf:.2f}) = {tot:.4f}",
            f"{ahp_tot:.4f}"
        ])

    steps.append(Step(
        id="pm.cf_sf",
        title=f"Step 4. Core Factor ({cf_weight*100:.0f}%) & Secondary Factor ({sf_weight*100:.0f}%)",
        explanation=(
            f"Core Factor (CF): {', '.join(core_factors)} | "
            f"Secondary Factor (SF): {', '.join(secondary_factors)}. "
            f"Total = ({cf_weight*100:.0f}% × NCF) + ({sf_weight*100:.0f}% × NSF)."
        ),
        table=TableData(
            columns=["Alternative", "NCF", "NSF", "Final Score (CF/SF)", "AHP-Weighted Score"],
            rows=step4_rows
        )
    ))

    # 8. Perangkingan
    ranks = rank_min(total_scores)

    # Step 5: Final ranking table
    sorted_alts = sorted(alternatives, key=lambda a: ranks[a])
    step5_rows = []
    for a in sorted_alts:
        step5_rows.append([
            str(ranks[a]),
            a,
            f"{total_scores[a]:.4f}",
            f"{ncf_scores[a]:.4f}",
            f"{nsf_scores[a]:.4f}"
        ])

    winner = sorted_alts[0]
    steps.append(Step(
        id="pm.ranking",
        title="Step 5. Final Profile Matching Ranking",
        explanation="Alternatives are ordered by the final Profile Matching total score from largest to smallest.",
        table=TableData(
            columns=["Rank", "Alternative", "Final Score", "NCF", "NSF"],
            rows=step5_rows
        ),
        result=ResultBox(
            text=f"Profile Matching winner ({dm_id}): {winner} with Final Score {total_scores[winner]:.4f}.",
            status="ok"
        )
    ))

    # Normalise scores to 0 - 1 for comparison
    mn_s = min(total_scores.values())
    mx_s = max(total_scores.values())
    normalized = {}
    for a in alternatives:
        if mx_s > mn_s:
            normalized[a] = (total_scores[a] - mn_s) / (mx_s - mn_s)
        else:
            normalized[a] = 1.0

    return ModelResult(
        model="PROFILE_MATCHING",
        scope="individual",
        dm_id=dm_id,
        scores=total_scores,
        ranks=ranks,
        steps=steps,
        normalized=normalized,
        extra={
            "core_factors": core_factors,
            "secondary_factors": secondary_factors,
            "cf_weight": cf_weight,
            "sf_weight": sf_weight,
            "ncf_scores": ncf_scores,
            "nsf_scores": nsf_scores,
            "target_levels": target_levels,
            "rating_matrix": rating_matrix,
            "gap_matrix": gap_matrix,
            "gap_weight_matrix": gap_weight_matrix,
            "ahp_weighted_scores": ahp_weighted_scores
        }
    )

def solve_profile_matching_group(
    dm_pm_scores: Dict[str, Dict[str, float]],
    dm_weights: Dict[str, float],
    alternatives: List[str]
) -> ModelResult:
    """
    GDSS group aggregation for Profile Matching:
    Group Score = Σ v_k × Score_PM,k
    """
    steps: List[Step] = []
    dms = list(dm_pm_scores.keys())

    # Step 1: PM scores per DM
    step1_rows = []
    for d in dms:
        w_d = dm_weights.get(d, 0.0)
        row = [d, f"{w_d:.4f}"]
        for a in alternatives:
            s = dm_pm_scores[d].get(a, 0.0)
            row.append(f"{s:.4f}")
        step1_rows.append(row)

    steps.append(Step(
        id="pm.group.input",
        title="Step 1. Profile Matching Score Matrix of Each DM and Facilitator Weight",
        explanation="Each DM has a Profile Matching score for every alternative and an influence weight from the Facilitator AHP.",
        table=TableData(
            columns=["DM", "Facilitator Weight"] + alternatives,
            rows=step1_rows
        )
    ))

    # Step 2: Weighted score aggregation
    group_scores: Dict[str, float] = {a: 0.0 for a in alternatives}
    step2_rows = []
    for a in alternatives:
        terms = []
        tot = 0.0
        for d in dms:
            w_d = dm_weights.get(d, 0.0)
            s_d = dm_pm_scores[d].get(a, 0.0)
            contrib = w_d * s_d
            tot += contrib
            terms.append(f"({w_d:.4f} × {s_d:.4f})")
        group_scores[a] = float(tot)
        step2_rows.append([a, " + ".join(terms), f"{tot:.4f}"])

    steps.append(Step(
        id="pm.group.aggregation",
        title="Step 2. Group Profile Matching Score Aggregation (Σ v_k × Score_k)",
        explanation="The group score is the sum of each DM's facilitator weight times that DM's Profile Matching score.",
        table=TableData(
            columns=["Alternative", "Rincian Penjumlahan", "Group Score"],
            rows=step2_rows
        )
    ))

    # Step 3: Group ranking
    ranks = rank_min(group_scores)
    sorted_alts = sorted(alternatives, key=lambda a: ranks[a])
    winner = sorted_alts[0]

    step3_rows = []
    for a in sorted_alts:
        step3_rows.append([str(ranks[a]), a, f"{group_scores[a]:.4f}"])

    steps.append(Step(
        id="pm.group.ranking",
        title="Step 3. Group GDSS Profile Matching Consensus Ranking",
        explanation="The group consensus ranking based on the Profile Matching method.",
        table=TableData(
            columns=["Rank", "Alternative", "GDSS Consensus Score"],
            rows=step3_rows
        ),
        result=ResultBox(
            text=f"Group Profile Matching consensus winner: {winner} (Score: {group_scores[winner]:.4f}).",
            status="ok"
        )
    ))

    # Normalise scores to 0 - 1
    mn_s = min(group_scores.values())
    mx_s = max(group_scores.values())
    normalized = {}
    for a in alternatives:
        if mx_s > mn_s:
            normalized[a] = (group_scores[a] - mn_s) / (mx_s - mn_s)
        else:
            normalized[a] = 1.0

    return ModelResult(
        model="PROFILE_MATCHING_GROUP",
        scope="group",
        dm_id=None,
        scores=group_scores,
        ranks=ranks,
        steps=steps,
        normalized=normalized
    )
