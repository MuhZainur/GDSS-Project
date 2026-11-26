import math
from typing import List, Dict, Any, Tuple
import numpy as np

from engine.schemas import (
    Step,
    TableData,
    MatrixData,
    ResultBox,
    ModelResult
)
from engine.ranking import rank_min

def solve_ahp_group_aip(
    dm_ahp_scores: Dict[str, Dict[str, float]], # dm_id -> {alt_id: ahp_score}
    dm_weights: Dict[str, float], # dm_id -> weight
    alternatives: List[str]
) -> ModelResult:
    """
    Solves Group AHP with the AIP method (Aggregation of Individual Priorities):
    Weighted geometric mean:
    g_k = prod_i (s_ik ^ v_i) = exp(sum_i v_i * ln(s_ik))
    Normalisation: G_k = g_k / sum(g)
    """
    dms = list(dm_weights.keys())
    steps: List[Step] = []
    warnings: List[str] = []

    # Step 1: AHP score table of each DM
    step1_rows = []
    for d in dms:
        row = [d, f"{dm_weights[d]:.4f}"]
        for a in alternatives:
            s_val = dm_ahp_scores[d].get(a, 0.0)
            row.append(f"{s_val:.4f}")
        step1_rows.append(row)

    steps.append(Step(
        id="ahp.group.input",
        title="Step 1. Individual AHP Priority Scores and DM Weights",
        explanation="Takes each DM's final AHP score and each DM's importance weight.",
        table=TableData(
            columns=["DM", "Importance Weight (v)"] + alternatives,
            rows=step1_rows
        )
    ))

    # Step 2: Weighted geometric mean
    g_scores = {}
    step2_rows = []

    for a in alternatives:
        terms = []
        log_sum = 0.0
        for d in dms:
            v_i = dm_weights[d]
            s_ik = dm_ahp_scores[d].get(a, 0.0)
            if s_ik <= 0:
                s_ik = 1e-12
                warnings.append(f"AHP score of {d} for {a} is <= 0, substituted with 1e-12.")
            log_sum += v_i * math.log(s_ik)
            terms.append(f"({s_ik:.4f}^{{{v_i:.4f}}})")

        g_val = math.exp(log_sum)
        g_scores[a] = g_val
        expr = f"{' × '.join(terms)} = {g_val:.6f}"
        step2_rows.append([a, expr, f"{g_val:.6f}"])

    sum_g = sum(g_scores.values())

    steps.append(Step(
        id="ahp.group.geometric",
        title="Step 2. Weighted Geometric Mean (AIP: g_k = ∏ s_{ik}^{v_i})",
        explanation="Each AHP score is raised to the DM weight and the results are multiplied: g_k = \\exp(\\sum v_i \\ln s_{ik}).",
        table=TableData(
            columns=["Alternative", "Geometric Mean Calculation", "Value g_k"],
            rows=step2_rows
        ),
        result=ResultBox(text=f"Total of g = {sum_g:.6f}", status="info")
    ))

    # Step 3: Normalise G_k
    G_scores = {}
    step3_rows = []
    for a in alternatives:
        g_norm = g_scores[a] / sum_g if sum_g > 0 else 0.0
        G_scores[a] = g_norm
        step3_rows.append([a, f"{g_scores[a]:.6f} ÷ {sum_g:.6f}", f"{g_norm:.4f}"])

    steps.append(Step(
        id="ahp.group.norm",
        title="Step 3. Group Score Normalisation (G_k = g_k / Σ g)",
        explanation="The geometric values are normalised so that all alternatives sum to 1.0 (100%).",
        table=TableData(
            columns=["Alternative", "Normalisation Calculation", "Group AHP Score (G)"],
            rows=step3_rows
        )
    ))

    # Step 4: Ranking
    ranks = rank_min(G_scores)
    step4_rows = []
    for a in alternatives:
        step4_rows.append([a, f"{G_scores[a]:.4f}", str(ranks[a])])
    step4_rows_sorted = sorted(step4_rows, key=lambda r: int(r[2]))

    steps.append(Step(
        id="ahp.group.rank",
        title="Step 4. Final Group AHP Ranking (AIP)",
        explanation="Alternatives are ordered from the largest group score G.",
        table=TableData(
            columns=["Alternative", "Group AHP Score", "Rank"],
            rows=step4_rows_sorted
        ),
        result=ResultBox(
            text=f"Group AHP winner: Alternative {step4_rows_sorted[0][0]} with score {step4_rows_sorted[0][1]}.",
            status="ok"
        )
    ))

    return ModelResult(
        model="AHP_GROUP_AIP",
        scope="group",
        scores=G_scores,
        ranks=ranks,
        steps=steps,
        meta={"sum_g": sum_g, "warnings": warnings}
    )
