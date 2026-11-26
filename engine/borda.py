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

def solve_borda_unweighted(
    dm_rankings: Dict[str, Dict[str, int]], # dm_id -> {alt_id: rank}
    alternatives: List[str]
) -> ModelResult:
    """
    Solves Unweighted Borda:
    For m alternatives: rank 1 = m-1 points, rank 2 = m-2 points, ..., rank m = 0 points.
    """
    num_alts = len(alternatives)
    dms = list(dm_rankings.keys())

    steps: List[Step] = []

    # Step 1: Rank table from each DM's reference model
    step1_rows = []
    for d in dms:
        row = [d]
        for a in alternatives:
            row.append(str(dm_rankings[d].get(a, "-")))
        step1_rows.append(row)

    steps.append(Step(
        id="borda.unweighted.input",
        title="Step 1. Alternative Rank Table from Each DM's Reference Model",
        explanation="Each DM provides the ranking preference of their own reference decision model.",
        table=TableData(
            columns=["Decision Maker (DM)"] + alternatives,
            rows=step1_rows
        )
    ))

    # Step 2: Rank frequency table
    # Rows: Rank 1..m (with their respective points)
    freq = {r: {a: 0 for a in alternatives} for r in range(1, num_alts + 1)}
    for d in dms:
        for a in alternatives:
            r = dm_rankings[d][a]
            if 1 <= r <= num_alts:
                freq[r][a] += 1

    step2_rows = []
    for r in range(1, num_alts + 1):
        pt = num_alts - r
        row = [f"Rank {r} (Points: {pt})"]
        for a in alternatives:
            row.append(str(freq[r][a]))
        step2_rows.append(row)

    steps.append(Step(
        id="borda.unweighted.freq",
        title="Step 2. Rank Position Frequency Table",
        explanation=f"Counts how many DMs placed each alternative at rank 1 up to {num_alts}.",
        table=TableData(
            columns=["Rank Position"] + alternatives,
            rows=step2_rows
        )
    ))

    # Step 3: Total Borda points
    points = {a: 0.0 for a in alternatives}
    step3_rows = []
    for a in alternatives:
        terms = []
        tot = 0
        for r in range(1, num_alts + 1):
            pt = num_alts - r
            count = freq[r][a]
            if count > 0:
                terms.append(f"({count} × {pt})")
            tot += count * pt
        points[a] = float(tot)
        expr = " + ".join(terms) if terms else "0"
        step3_rows.append([a, f"{expr} = {tot}", str(tot)])

    total_all_points = sum(points.values())
    steps.append(Step(
        id="borda.unweighted.points",
        title="Step 3. Total Borda Points (Σ Frequency × Rank Weight)",
        explanation="Total points are the frequency of each rank times the point weight of that position.",
        table=TableData(
            columns=["Alternative", "Points Sum Breakdown", "Total Points"],
            rows=step3_rows
        ),
        result=ResultBox(text=f"Overall total of Borda points = {total_all_points:.0f}", status="info")
    ))

    # Step 4: Normalise point weights
    normalized = {}
    step4_rows = []
    for a in alternatives:
        norm_val = points[a] / total_all_points if total_all_points > 0 else 0.0
        normalized[a] = round(norm_val, 4)
        step4_rows.append([a, f"{points[a]:.0f} ÷ {total_all_points:.0f}", f"{norm_val:.4f}"])

    steps.append(Step(
        id="borda.unweighted.normalized",
        title="Step 4. Final Weight Normalisation",
        explanation="The final weight is each alternative's points divided by the overall total of points.",
        table=TableData(
            columns=["Alternative", "Normalisation Calculation", "Final Weight"],
            rows=step4_rows
        )
    ))

    # Step 5: Ranking
    ranks = rank_min(points)
    step5_rows = []
    for a in alternatives:
        step5_rows.append([a, f"{points[a]:.0f}", f"{normalized[a]:.4f}", str(ranks[a])])
    step5_rows_sorted = sorted(step5_rows, key=lambda r: int(r[3]))

    steps.append(Step(
        id="borda.unweighted.rank",
        title="Step 5. Final Unweighted Borda Ranking",
        explanation="Alternatives are ordered by the highest total Borda points.",
        table=TableData(
            columns=["Alternative", "Total Points", "Relative Weight", "Rank"],
            rows=step5_rows_sorted
        ),
        result=ResultBox(
            text=f"Winner Borda Tanpa Weight: Alternative {step5_rows_sorted[0][0]} with points {step5_rows_sorted[0][1]}.",
            status="ok"
        )
    ))

    return ModelResult(
        model="BORDA_UNWEIGHTED",
        scope="group",
        scores=points,
        ranks=ranks,
        steps=steps,
        normalized=normalized
    )

def solve_borda_weighted(
    dm_rankings: Dict[str, Dict[str, int]], # dm_id -> {alt_id: rank}
    dm_weights: Dict[str, float], # dm_id -> weight
    alternatives: List[str]
) -> ModelResult:
    """
    Solves Weighted Borda:
    B_k = sum_i v_i * (m - r_ik)
    Normalized = B_k / sum(B)
    Equivalence: B_k = m - sum_i (v_i * r_ik)
    """
    num_alts = len(alternatives)
    dms = list(dm_weights.keys())

    steps: List[Step] = []

    # Step 1: DM ranks and weights
    step1_rows = []
    for d in dms:
        row = [d, f"{dm_weights[d]:.4f}"]
        for a in alternatives:
            row.append(str(dm_rankings[d][a]))
        step1_rows.append(row)

    steps.append(Step(
        id="borda.weighted.input",
        title="Step 1. DM Ranks and Importance Weights",
        explanation="Each DM's weight comes from the pairwise comparison matrix between DMs in the facilitator AHP.",
        table=TableData(
            columns=["DM", "Importance Weight (v)"] + alternatives,
            rows=step1_rows
        )
    ))

    # Step 2: Weighted points B_k
    scores: Dict[str, float] = {}
    contributions: Dict[str, Dict[str, float]] = {}
    step2_rows = []

    for a in alternatives:
        contributions[a] = {}
        terms = []
        equiv_terms = []
        b_val = 0.0
        equiv_val = 0.0

        for d in dms:
            v_i = dm_weights[d]
            r_ik = dm_rankings[d][a]
            pt = num_alts - r_ik
            c_val = v_i * pt
            contributions[a][d] = round(c_val, 4)
            b_val += c_val
            equiv_val += v_i * r_ik
            terms.append(f"({v_i:.4f} × {pt})")
            equiv_terms.append(f"({v_i:.4f} × {r_ik})")

        scores[a] = b_val
        expr = f"{' + '.join(terms)} = {b_val:.4f}"
        equiv_expr = f"{num_alts} - ({' + '.join(equiv_terms)}) = {num_alts - equiv_val:.4f}"
        step2_rows.append([a, expr, equiv_expr, f"{b_val:.4f}"])

    sum_B = sum(scores.values())

    steps.append(Step(
        id="borda.weighted.calc",
        title="Step 2. Weighted Borda Score Calculation (B_k = Σ v_i · (m − r_{ik}))",
        explanation="Each rank is converted to points (m - rank) and multiplied by the DM weight. The equivalence column shows the equivalent formula: m - Σ(v · rank).",
        table=TableData(
            columns=["Alternative", "Standard Formula (Σ v × (m-r))", "Equivalent Formula (m - Σ v×r)", "Borda Score (B)"],
            rows=step2_rows
        ),
        result=ResultBox(text=f"Total Weighted Borda Score (Σ B) = {sum_B:.4f}", status="info")
    ))

    # Step 3: Final weight normalisation
    normalized = {}
    step3_rows = []
    for a in alternatives:
        norm_val = scores[a] / sum_B if sum_B > 0 else 0.0
        normalized[a] = round(norm_val, 4)
        step3_rows.append([a, f"{scores[a]:.4f} ÷ {sum_B:.4f}", f"{norm_val:.4f}"])

    steps.append(Step(
        id="borda.weighted.norm",
        title="Step 3. Final Relative Weight of Weighted Borda",
        explanation="Normalisation divides each Borda score by the total Borda score.",
        table=TableData(
            columns=["Alternative", "Normalisation Calculation", "Final Weight"],
            rows=step3_rows
        )
    ))

    # Step 4: Ranking
    ranks = rank_min(scores)
    step4_rows = []
    for a in alternatives:
        step4_rows.append([a, f"{scores[a]:.4f}", f"{normalized[a]:.4f}", str(ranks[a])])
    step4_rows_sorted = sorted(step4_rows, key=lambda r: int(r[3]))

    steps.append(Step(
        id="borda.weighted.rank",
        title="Step 4. Final Weighted Borda Ranking",
        explanation="Alternatives are ordered from the largest to the smallest weighted Borda score.",
        table=TableData(
            columns=["Alternative", "Weighted Borda Score", "Relative Weight", "Rank"],
            rows=step4_rows_sorted
        ),
        result=ResultBox(
            text=f"Weighted Borda winner: Alternative {step4_rows_sorted[0][0]} with score {step4_rows_sorted[0][1]}.",
            status="ok"
        )
    ))

    return ModelResult(
        model="BORDA_WEIGHTED",
        scope="group",
        scores=scores,
        ranks=ranks,
        steps=steps,
        normalized=normalized,
        contributions=contributions
    )
