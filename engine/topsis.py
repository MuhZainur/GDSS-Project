from typing import List, Dict, Any, Tuple
import numpy as np

from engine.schemas import (
    Step,
    TableData,
    MatrixData,
    ResultBox,
    ModelResult
)
from engine.ahp import to_latex_matrix
from engine.ranking import rank_min

def solve_topsis_individual(
    dm_id: str,
    criteria: List[str],
    criteria_weights: np.ndarray,
    alternatives: List[str],
    criteria_types: Dict[str, str], # crit_id -> "benefit" | "cost"
    values: Dict[str, Dict[str, float]] # alt_id -> {crit_id: float}
) -> ModelResult:
    """
    Solves the TOPSIS model for one DM:
    - Step 1: Decision matrix (X)
    - Step 2: Matrix divisor d_j = sqrt(sum(v_j^2))
    - Step 3: Vector-normalised matrix (R)
    - Step 4: Weighted normalised matrix (Y)
    - Step 5: Positive (A+) and negative (A-) ideal solutions
    - Step 6: Distances D+ and D-
    - Step 7: Relative closeness (V)
    - Step 8: Ranking
    """
    num_alts = len(alternatives)
    num_crits = len(criteria)
    w = np.array(criteria_weights, dtype=np.float64)

    # Step 1: Raw decision matrix
    V = np.zeros((num_alts, num_crits), dtype=np.float64)
    step1_rows = []
    for i, a in enumerate(alternatives):
        row = [a]
        for j, c in enumerate(criteria):
            val = values[a][c]
            V[i, j] = val
            row.append(f"{val:.4f}" if isinstance(val, float) else str(val))
        step1_rows.append(row)

    steps: List[Step] = []
    steps.append(Step(
        id=f"topsis.{dm_id}.raw",
        title="Step 1. Decision Matrix (X)",
        explanation="The raw value matrix of the alternatives on the criteria chosen by the DM.",
        table=TableData(
            columns=["Alternative"] + criteria,
            rows=step1_rows
        ),
        matrix=MatrixData(latex=f"X = {to_latex_matrix(V)}")
    ))

    # Step 2: Divisor d_j
    divisors = np.sqrt(np.sum(V ** 2, axis=0))
    step2_rows = []
    for j, c in enumerate(criteria):
        sq_terms = [f"{V[i, j]:.1f}²" for i in range(num_alts)]
        sum_sq = np.sum(V[:, j] ** 2)
        expr = f"√({' + '.join(sq_terms)}) = √({sum_sq:.2f}) = {divisors[j]:.4f}"
        step2_rows.append([c, expr, f"{divisors[j]:.4f}"])

    steps.append(Step(
        id=f"topsis.{dm_id}.divisors",
        title="Step 2. Vector Normalisation Divisor (d_j)",
        explanation="Computes the square root of the sum of squared elements for each criterion: d_j = \\sqrt{\\sum_k v_{kj}^2}.",
        table=TableData(
            columns=["Criterion", "Square Root Calculation", "Divisor Value (d_j)"],
            rows=step2_rows
        )
    ))

    # Step 3: Normalise matrix R
    R = V / divisors
    step3_rows = []
    for i, a in enumerate(alternatives):
        row = [a]
        for j, c in enumerate(criteria):
            row.append(f"{V[i, j]:.2f} ÷ {divisors[j]:.2f} = {R[i, j]:.4f}")
        step3_rows.append(row)

    steps.append(Step(
        id=f"topsis.{dm_id}.norm",
        title="Step 3. Vector-Normalised Matrix (R)",
        explanation="Each matrix element is divided by the divisor of its criterion: r_{kj} = v_{kj} / d_j.",
        table=TableData(
            columns=["Alternative"] + criteria,
            rows=step3_rows
        ),
        matrix=MatrixData(latex=f"R = {to_latex_matrix(R)}")
    ))

    # Step 4: Weighted matrix Y = R * w
    Y = R * w
    step4_rows = []
    for i, a in enumerate(alternatives):
        row = [a]
        for j, c in enumerate(criteria):
            row.append(f"{w[j]:.4f} × {R[i, j]:.4f} = {Y[i, j]:.4f}")
        step4_rows.append(row)

    steps.append(Step(
        id=f"topsis.{dm_id}.weighted",
        title="Step 4. Weighted Normalised Matrix (Y)",
        explanation="Multiplies the normalised matrix elements by the AHP criteria weights: y_{kj} = w_j \\cdot r_{kj}.",
        table=TableData(
            columns=["Alternative"] + criteria,
            rows=step4_rows
        ),
        matrix=MatrixData(latex=f"Y = {to_latex_matrix(Y)}")
    ))

    # Step 5: Positive (A+) and negative (A-) ideal solutions
    A_plus = np.zeros(num_crits, dtype=np.float64)
    A_minus = np.zeros(num_crits, dtype=np.float64)

    for j, c in enumerate(criteria):
        c_type = criteria_types[c]
        if c_type == "cost":
            A_plus[j] = np.min(Y[:, j])
            A_minus[j] = np.max(Y[:, j])
        else:
            A_plus[j] = np.max(Y[:, j])
            A_minus[j] = np.min(Y[:, j])

    step5_rows = [
        ["Positive Ideal Solution (A+)"] + [f"{A_plus[j]:.4f}" for j in range(num_crits)],
        ["Negative Ideal Solution (A-)"] + [f"{A_minus[j]:.4f}" for j in range(num_crits)]
    ]

    steps.append(Step(
        id=f"topsis.{dm_id}.ideals",
        title="Step 5. Positive (A+) and Negative (A-) Ideal Solutions",
        explanation="Benefit: A+ is the maximum value, A- the minimum. Cost: A+ is the minimum value, A- the maximum.",
        table=TableData(
            columns=["Ideal Solution"] + criteria,
            rows=step5_rows
        )
    ))

    # Step 6: Distances D+ and D-
    D_plus = np.sqrt(np.sum((Y - A_plus) ** 2, axis=1))
    D_minus = np.sqrt(np.sum((Y - A_minus) ** 2, axis=1))

    step6_rows = []
    for i, a in enumerate(alternatives):
        step6_rows.append([a, f"{D_plus[i]:.4f}", f"{D_minus[i]:.4f}"])

    steps.append(Step(
        id=f"topsis.{dm_id}.distances",
        title="Step 6. Euclidean Distance to the Ideal Solutions (D+ and D-)",
        explanation="D+ is the distance to the positive ideal solution, D- the distance to the negative ideal solution.",
        table=TableData(
            columns=["Alternative", "Distance to A+ (D+)", "Distance to A- (D-)"],
            rows=step6_rows
        )
    ))

    # Step 7: Relative closeness (V)
    denom = D_plus + D_minus
    V_scores = np.zeros(num_alts, dtype=np.float64)
    warnings = []
    step7_rows = []

    for i, a in enumerate(alternatives):
        if denom[i] == 0:
            v_val = 0.5
            warnings.append(f"Alternative {a} has D+ + D- = 0 (identical to the ideal), V is set to 0.5.")
            step7_rows.append([a, "0 ÷ 0 → diset khusus 0.5", "0.5000"])
        else:
            v_val = float(D_minus[i] / denom[i])
            step7_rows.append([a, f"{D_minus[i]:.4f} ÷ ({D_plus[i]:.4f} + {D_minus[i]:.4f})", f"{v_val:.4f}"])
        V_scores[i] = v_val

    steps.append(Step(
        id=f"topsis.{dm_id}.closeness",
        title="Step 7. Preference Value / Relative Closeness (V)",
        explanation="The relative closeness to the ideal solution is computed with the formula: V_k = D-_k / (D+_k + D-_k).",
        table=TableData(
            columns=["Alternative", "V_k Calculation", "Preference Score (V)"],
            rows=step7_rows
        ),
        matrix=MatrixData(latex=f"V = {to_latex_matrix(V_scores.reshape(-1, 1))}")
    ))

    # Step 8: Ranking
    scores_dict = {a: float(V_scores[i]) for i, a in enumerate(alternatives)}
    ranks_dict = rank_min(scores_dict)

    step8_rows = []
    for i, a in enumerate(alternatives):
        step8_rows.append([a, f"{V_scores[i]:.4f}", str(ranks_dict[a])])
    step8_rows_sorted = sorted(step8_rows, key=lambda r: int(r[2]))

    steps.append(Step(
        id=f"topsis.{dm_id}.rank",
        title="Step 8. Final TOPSIS Ranking",
        explanation="Alternatives are ordered from the largest preference value V to the smallest.",
        table=TableData(
            columns=["Alternative", "Closeness Score (V)", "Rank"],
            rows=step8_rows_sorted
        ),
        result=ResultBox(
            text=f"TOPSIS winner ({dm_id}): Alternative {step8_rows_sorted[0][0]} with closeness {step8_rows_sorted[0][1]}.",
            status="ok"
        )
    ))

    d_plus_dict = {a: float(D_plus[i]) for i, a in enumerate(alternatives)}
    d_minus_dict = {a: float(D_minus[i]) for i, a in enumerate(alternatives)}

    return ModelResult(
        model="TOPSIS",
        scope="individual",
        dm_id=dm_id,
        scores=scores_dict,
        ranks=ranks_dict,
        steps=steps,
        extra={
            "d_plus": d_plus_dict,
            "d_minus": d_minus_dict,
            "warnings": warnings
        }
    )

def solve_topsis_group(
    dm_topsis_scores: Dict[str, Dict[str, float]],
    dm_weights: Dict[str, float],
    alternatives: List[str]
) -> ModelResult:
    """
    GDSS group aggregation for TOPSIS:
    Group Score = Σ v_k × Score_TOPSIS,k
    """
    steps: List[Step] = []
    dms = list(dm_topsis_scores.keys())

    # Step 1: TOPSIS scores per DM
    step1_rows = []
    for d in dms:
        w_d = dm_weights.get(d, 0.0)
        row = [d, f"{w_d:.4f}"]
        for a in alternatives:
            s = dm_topsis_scores[d].get(a, 0.0)
            row.append(f"{s:.4f}")
        step1_rows.append(row)

    steps.append(Step(
        id="topsis.group.input",
        title="Step 1. TOPSIS Closeness Score Matrix (V) of Each DM and Facilitator Weight",
        explanation="Each DM has a TOPSIS preference value (V) for every alternative and an influence weight from the Facilitator AHP.",
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
            s_d = dm_topsis_scores[d].get(a, 0.0)
            contrib = w_d * s_d
            tot += contrib
            terms.append(f"({w_d:.4f} × {s_d:.4f})")
        group_scores[a] = float(tot)
        step2_rows.append([a, " + ".join(terms), f"{tot:.4f}"])

    steps.append(Step(
        id="topsis.group.aggregation",
        title="Step 2. Group TOPSIS Score Aggregation (Σ v_k × V_k)",
        explanation="The group score is the sum of each DM's facilitator weight times that DM's TOPSIS preference value.",
        table=TableData(
            columns=["Alternative", "Rincian Penjumlahan", "Group TOPSIS Score"],
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
        id="topsis.group.ranking",
        title="Step 3. Group GDSS TOPSIS Consensus Ranking",
        explanation="The group consensus ranking based on the TOPSIS method.",
        table=TableData(
            columns=["Rank", "Alternative", "GDSS Consensus Score"],
            rows=step3_rows
        ),
        result=ResultBox(
            text=f"Group TOPSIS consensus winner: {winner} (Score: {group_scores[winner]:.4f}).",
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
        model="TOPSIS_GROUP",
        scope="group",
        dm_id=None,
        scores=group_scores,
        ranks=ranks,
        steps=steps,
        normalized=normalized
    )
