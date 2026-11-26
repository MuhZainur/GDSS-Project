from typing import List, Dict, Any
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

def solve_wp_individual(
    dm_id: str,
    criteria: List[str],
    criteria_weights: np.ndarray,
    alternatives: List[str],
    criteria_types: Dict[str, str], # crit_id -> "benefit" | "cost"
    values: Dict[str, Dict[str, float]] # alt_id -> {crit_id: float}
) -> ModelResult:
    """
    Solves the Weighted Product (WP) model for one DM:
    - Step 1: Raw decision matrix (X)
    - Step 2: Weight exponent w* (+w for benefit, -w for cost)
    - Step 3: S vector (S_i = prod(x_ij ^ w_j*))
    - Step 4: V vector (V_i = S_i / sum(S))
    - Step 5: Ranking preferensi relatif
    """
    num_alts = len(alternatives)
    num_crits = len(criteria)
    raw_w = np.array(criteria_weights, dtype=np.float64)
    # Normalise the weights if they do not sum to exactly 1
    w_sum = np.sum(raw_w)
    norm_w = raw_w / w_sum if w_sum > 0 else raw_w

    # Step 1: Decision matrix
    X = np.zeros((num_alts, num_crits), dtype=np.float64)
    step1_rows = []
    for i, a in enumerate(alternatives):
        row = [a]
        for j, c in enumerate(criteria):
            val = values[a][c]
            X[i, j] = val
            row.append(f"{val:.4f}" if isinstance(val, float) else str(val))
        step1_rows.append(row)

    steps: List[Step] = []
    steps.append(Step(
        id=f"wp.{dm_id}.raw",
        title="Step 1. Decision Matrix (X)",
        explanation="The decision matrix holds the quantitative value of every alternative on the assessed criteria.",
        table=TableData(
            columns=["Alternative"] + criteria,
            rows=step1_rows
        ),
        matrix=MatrixData(latex=f"X = {to_latex_matrix(X)}")
    ))

    # Step 2: Determine the weight exponent w*
    power_w = np.zeros(num_crits, dtype=np.float64)
    step2_rows = []
    for j, c in enumerate(criteria):
        c_type = criteria_types[c]
        if c_type == "cost":
            power_w[j] = -norm_w[j]
            formula_str = f"-{norm_w[j]:.4f} (Cost)"
        else:
            power_w[j] = norm_w[j]
            formula_str = f"+{norm_w[j]:.4f} (Benefit)"
        step2_rows.append([c, c_type, f"{norm_w[j]:.4f}", formula_str])

    steps.append(Step(
        id=f"wp.{dm_id}.powers",
        title="Step 2. Weight Exponent Calculation (w*)",
        explanation="In WP, benefit criteria get a positive exponent (+w) and cost criteria a negative exponent (-w).",
        table=TableData(
            columns=["Criterion", "Tipe", "AHP Weight", "Weight Exponent (w*)"],
            rows=step2_rows
        )
    ))

    # Step 3: S vector
    # S_i = prod_j (X_ij ^ power_w_j)
    S = np.zeros(num_alts, dtype=np.float64)
    step3_rows = []
    for i, a in enumerate(alternatives):
        terms = []
        prod_val = 1.0
        for j, c in enumerate(criteria):
            term_val = float(X[i, j] ** power_w[j])
            prod_val *= term_val
            terms.append(f"({X[i, j]:.2f}^{{{power_w[j]:.4f}}})")
        S[i] = prod_val
        step3_rows.append([a, " × ".join(terms), f"{S[i]:.6f}"])

    sum_S = float(np.sum(S))
    steps.append(Step(
        id=f"wp.{dm_id}.vector_s",
        title="Step 3. S Vector Calculation (S_i = ∏ x_{ij}^{w_j*})",
        explanation="The S vector is obtained by multiplying all criteria values, each raised to the exponent of its weight.",
        table=TableData(
            columns=["Alternative", "Perkalian Perpangkatan", "S Vector Value"],
            rows=step3_rows
        ),
        result=ResultBox(text=f"Total S Vector (Σ S) = {sum_S:.6f}", status="info")
    ))

    # Step 4: V vector (relative preference)
    V = S / sum_S if sum_S > 0 else np.zeros_like(S)
    step4_rows = []
    for i, a in enumerate(alternatives):
        step4_rows.append([a, f"{S[i]:.6f} ÷ {sum_S:.6f}", f"{V[i]:.4f}"])

    steps.append(Step(
        id=f"wp.{dm_id}.vector_v",
        title="Step 4. Relative Preference Vector Calculation (V_i = S_i / Σ S)",
        explanation="The relative preference V_i is each alternative's S_i divided by the total of all S values.",
        table=TableData(
            columns=["Alternative", "Calculation (S_i ÷ Σ S)", "V Vector Value"],
            rows=step4_rows
        ),
        matrix=MatrixData(latex=f"V = {to_latex_matrix(V.reshape(-1, 1))}"),
        result=ResultBox(text="All V vector values sum to 1.0000 (100%).", status="info")
    ))

    # Step 5: Ranking
    scores_dict = {a: float(V[i]) for i, a in enumerate(alternatives)}
    ranks_dict = rank_min(scores_dict)

    step5_rows = []
    for i, a in enumerate(alternatives):
        step5_rows.append([a, f"{V[i]:.4f}", str(ranks_dict[a])])
    step5_rows_sorted = sorted(step5_rows, key=lambda r: int(r[2]))

    steps.append(Step(
        id=f"wp.{dm_id}.rank",
        title="Step 5. Final Weighted Product (WP) Ranking",
        explanation="Alternatives are ordered from the largest V vector value (rank 1) to the smallest.",
        table=TableData(
            columns=["Alternative", "Preference Value (V)", "Rank"],
            rows=step5_rows_sorted
        ),
        result=ResultBox(
            text=f"WP winner ({dm_id}): Alternative {step5_rows_sorted[0][0]} with score V = {step5_rows_sorted[0][1]}.",
            status="ok"
        )
    ))

    return ModelResult(
        model="WP",
        scope="individual",
        dm_id=dm_id,
        scores=scores_dict,
        ranks=ranks_dict,
        steps=steps,
        meta={"sum_S": sum_S}
    )

def solve_wp_group(
    dm_wp_scores: Dict[str, Dict[str, float]],
    dm_weights: Dict[str, float],
    alternatives: List[str]
) -> ModelResult:
    """
    GDSS group aggregation for Weighted Product (WP):
    Group Score = Σ v_k × Score_WP,k
    """
    steps: List[Step] = []
    dms = list(dm_wp_scores.keys())

    # Step 1: WP scores per DM
    step1_rows = []
    for d in dms:
        w_d = dm_weights.get(d, 0.0)
        row = [d, f"{w_d:.4f}"]
        for a in alternatives:
            s = dm_wp_scores[d].get(a, 0.0)
            row.append(f"{s:.4f}")
        step1_rows.append(row)

    steps.append(Step(
        id="wp.group.input",
        title="Step 1. WP Preference Score Matrix (V) of Each DM and Facilitator Weight",
        explanation="Each DM has a WP preference value (V) for every alternative and an influence weight from the Facilitator AHP.",
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
            s_d = dm_wp_scores[d].get(a, 0.0)
            contrib = w_d * s_d
            tot += contrib
            terms.append(f"({w_d:.4f} × {s_d:.4f})")
        group_scores[a] = float(tot)
        step2_rows.append([a, " + ".join(terms), f"{tot:.4f}"])

    steps.append(Step(
        id="wp.group.aggregation",
        title="Step 2. Group WP Score Aggregation (Σ v_k × V_k)",
        explanation="The group score is the sum of each DM's facilitator weight times that DM's WP preference value.",
        table=TableData(
            columns=["Alternative", "Rincian Penjumlahan", "Group WP Score"],
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
        id="wp.group.ranking",
        title="Step 3. Group GDSS WP Consensus Ranking",
        explanation="The group consensus ranking based on the Weighted Product (WP) method.",
        table=TableData(
            columns=["Rank", "Alternative", "GDSS Consensus Score"],
            rows=step3_rows
        ),
        result=ResultBox(
            text=f"Group WP consensus winner: {winner} (Score: {group_scores[winner]:.4f}).",
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
        model="WP_GROUP",
        scope="group",
        dm_id=None,
        scores=group_scores,
        ranks=ranks,
        steps=steps,
        normalized=normalized
    )
