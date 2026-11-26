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

def solve_saw_individual(
    dm_id: str,
    criteria: List[str],
    criteria_weights: np.ndarray,
    alternatives: List[str],
    criteria_types: Dict[str, str], # crit_id -> "benefit" | "cost"
    values: Dict[str, Dict[str, float]] # alt_id -> {crit_id: float}
) -> ModelResult:
    """
    Solves the SAW model for one DM:
    - Step 1: Decision matrix
    - Step 2: Normalisation (benefit: v/max, cost: min/v)
    - Step 3: Criteria weights (from AHP)
    - Step 4: SAW Score (S = sum(w * r))
    - Step 5: Ranking
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
            v_val = values[a][c]
            V[i, j] = v_val
            row.append(f"{v_val:.4f}" if isinstance(v_val, float) else str(v_val))
        step1_rows.append(row)

    steps: List[Step] = []
    steps.append(Step(
        id=f"saw.{dm_id}.raw",
        title="Step 1. Decision Matrix (X)",
        explanation="The initial decision matrix holds the raw value of every alternative on the criteria assessed by the DM.",
        table=TableData(
            columns=["Alternative"] + criteria,
            rows=step1_rows
        ),
        matrix=MatrixData(latex=f"X = {to_latex_matrix(V)}")
    ))

    # Step 2: Normalisation
    R = np.zeros((num_alts, num_crits), dtype=np.float64)
    step2_rows = []
    max_vals = np.max(V, axis=0)
    min_vals = np.min(V, axis=0)

    for i, a in enumerate(alternatives):
        row = [a]
        for j, c in enumerate(criteria):
            c_type = criteria_types[c]
            if c_type == "cost":
                r_val = min_vals[j] / V[i, j]
                R[i, j] = r_val
                row.append(f"{min_vals[j]:.2f} ÷ {V[i, j]:.2f} = {r_val:.4f}")
            else:
                r_val = V[i, j] / max_vals[j]
                R[i, j] = r_val
                row.append(f"{V[i, j]:.2f} ÷ {max_vals[j]:.2f} = {r_val:.4f}")
        step2_rows.append(row)

    steps.append(Step(
        id=f"saw.{dm_id}.norm",
        title="Step 2. Matrix Normalisation (R)",
        explanation="Benefit normalisation: r_{kj} = v_{kj} / max(v_j); cost: r_{kj} = min(v_j) / v_{kj}.",
        table=TableData(
            columns=["Alternative"] + criteria,
            rows=step2_rows
        ),
        matrix=MatrixData(latex=f"R = {to_latex_matrix(R)}")
    ))

    # Step 3: AHP criteria weights
    step3_rows = [[c, criteria_types[c], f"{w[j]:.4f}"] for j, c in enumerate(criteria)]
    steps.append(Step(
        id=f"saw.{dm_id}.weights",
        title="Step 3. Criteria Weights (w from AHP)",
        explanation="The criteria weights come from the AHP calculation of the DM concerned.",
        table=TableData(
            columns=["Criterion", "Tipe", "Weight (w)"],
            rows=step3_rows
        )
    ))

    # Step 4: SAW Score
    # S = R * w
    saw_scores = np.dot(R, w)
    contributions: Dict[str, Dict[str, float]] = {}

    step4_rows = []
    for i, a in enumerate(alternatives):
        contributions[a] = {}
        terms = []
        for j, c in enumerate(criteria):
            c_contrib = float(w[j] * R[i, j])
            contributions[a][c] = round(c_contrib, 6)
            terms.append(f"({w[j]:.4f} × {R[i, j]:.4f})")
        expr = f"{' + '.join(terms)} = {saw_scores[i]:.4f}"
        step4_rows.append([a, expr, f"{saw_scores[i]:.4f}"])

    steps.append(Step(
        id=f"saw.{dm_id}.scores",
        title="Step 4. SAW Score Calculation (S_k = Σ w_j · r_{kj})",
        explanation="Each alternative's score is the sum of the criteria weights times the normalised values.",
        table=TableData(
            columns=["Alternative", "Calculation (Σ w × r)", "SAW Score"],
            rows=step4_rows
        ),
        matrix=MatrixData(latex=f"R \\times w = {to_latex_matrix(saw_scores.reshape(-1, 1))}")
    ))

    # Step 5: Ranking
    scores_dict = {a: float(saw_scores[i]) for i, a in enumerate(alternatives)}
    ranks_dict = rank_min(scores_dict)

    step5_rows = []
    for i, a in enumerate(alternatives):
        step5_rows.append([a, f"{saw_scores[i]:.4f}", str(ranks_dict[a])])
    step5_rows_sorted = sorted(step5_rows, key=lambda r: int(r[2]))

    steps.append(Step(
        id=f"saw.{dm_id}.rank",
        title="Step 5. Final SAW Ranking",
        explanation="Alternatives are ordered by SAW score from highest to lowest.",
        table=TableData(
            columns=["Alternative", "SAW Score", "Rank"],
            rows=step5_rows_sorted
        ),
        result=ResultBox(
            text=f"SAW winner ({dm_id}): Alternative {step5_rows_sorted[0][0]} with score {step5_rows_sorted[0][1]}.",
            status="ok"
        )
    ))

    return ModelResult(
        model="SAW",
        scope="individual",
        dm_id=dm_id,
        scores=scores_dict,
        ranks=ranks_dict,
        steps=steps,
        contributions=contributions
    )

def solve_saw_group(
    dm_saw_scores: Dict[str, Dict[str, float]],
    dm_weights: Dict[str, float],
    alternatives: List[str]
) -> ModelResult:
    """
    GDSS group aggregation for SAW:
    Group Score = Σ v_k × Score_SAW,k
    """
    steps: List[Step] = []
    dms = list(dm_saw_scores.keys())

    # Step 1: SAW scores per DM
    step1_rows = []
    for d in dms:
        w_d = dm_weights.get(d, 0.0)
        row = [d, f"{w_d:.4f}"]
        for a in alternatives:
            s = dm_saw_scores[d].get(a, 0.0)
            row.append(f"{s:.4f}")
        step1_rows.append(row)

    steps.append(Step(
        id="saw.group.input",
        title="Step 1. SAW Score Matrix of Each DM and Facilitator Weight",
        explanation="Each DM has a SAW score for every alternative and an influence weight from the Facilitator AHP.",
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
            s_d = dm_saw_scores[d].get(a, 0.0)
            contrib = w_d * s_d
            tot += contrib
            terms.append(f"({w_d:.4f} × {s_d:.4f})")
        group_scores[a] = float(tot)
        step2_rows.append([a, " + ".join(terms), f"{tot:.4f}"])

    steps.append(Step(
        id="saw.group.aggregation",
        title="Step 2. Group SAW Score Aggregation (Σ v_k × Score_k)",
        explanation="The group score is the sum of each DM's facilitator weight times that DM's SAW score.",
        table=TableData(
            columns=["Alternative", "Rincian Penjumlahan", "Group SAW Score"],
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
        id="saw.group.ranking",
        title="Step 3. Group GDSS SAW Consensus Ranking",
        explanation="The group consensus ranking based on the Simple Additive Weighting (SAW) method.",
        table=TableData(
            columns=["Rank", "Alternative", "GDSS Consensus Score"],
            rows=step3_rows
        ),
        result=ResultBox(
            text=f"Group SAW consensus winner: {winner} (Score: {group_scores[winner]:.4f}).",
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
        model="SAW_GROUP",
        scope="group",
        dm_id=None,
        scores=group_scores,
        ranks=ranks,
        steps=steps,
        normalized=normalized
    )
