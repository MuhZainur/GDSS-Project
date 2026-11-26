import math
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
from fractions import Fraction

from engine.fractions_util import (
    parse_fraction,
    fraction_to_float,
    format_fraction,
    format_saaty_display
)
from engine.schemas import (
    Step,
    TableData,
    MatrixData,
    ResultBox,
    ModelResult
)

# Saaty Random Index (RI) table
RI_DICT = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49
}

SAATY_VALUES = [
    Fraction(1, 9), Fraction(1, 8), Fraction(1, 7), Fraction(1, 6), Fraction(1, 5),
    Fraction(1, 4), Fraction(1, 3), Fraction(1, 2), Fraction(1, 1),
    Fraction(2, 1), Fraction(3, 1), Fraction(4, 1), Fraction(5, 1),
    Fraction(6, 1), Fraction(7, 1), Fraction(8, 1), Fraction(9, 1)
]

def nearest_saaty(val: float) -> str:
    """Finds the nearest Saaty scale value for a given float."""
    best = SAATY_VALUES[0]
    best_diff = abs(float(best) - val)
    for s in SAATY_VALUES[1:]:
        diff = abs(float(s) - val)
        if diff < best_diff:
            best_diff = diff
            best = s
    return format_fraction(best)

def to_latex_matrix(matrix: np.ndarray, decimals: int = 4) -> str:
    """Mengonversi 2D numpy array ke string LaTeX bmatrix."""
    rows_str = []
    for row in matrix:
        cols_str = [f"{val:.{decimals}f}" for val in row]
        rows_str.append(" & ".join(cols_str))
    return "\\begin{bmatrix}\n" + " \\\\\n".join(rows_str) + "\n\\end{bmatrix}"

def calculate_ahp_weights(
    pairwise_raw: List[List[Union[str, int, float]]],
    labels: List[str],
    prefix_id: str = "ahp"
) -> Tuple[np.ndarray, float, float, float, List[Step], List[Dict[str, Any]]]:
    """
    Computes AHP weights (Steps 1-5):
    Returns (weights, lambda_max, CI, CR, steps, suggestions).
    """
    n = len(labels)
    # Parse matrix A
    A = np.zeros((n, n), dtype=np.float64)
    A_raw_str = []
    for i in range(n):
        row_str = []
        for j in range(n):
            val = pairwise_raw[i][j]
            flt = fraction_to_float(val)
            A[i, j] = flt
            row_str.append(format_fraction(val))
        A_raw_str.append(row_str)

    steps: List[Step] = []

    # Step 1: Pairwise comparison matrix
    step1_rows = []
    for i in range(n):
        row = [labels[i]]
        for j in range(n):
            row.append(format_saaty_display(A_raw_str[i][j]))
        step1_rows.append(row)
    
    step1 = Step(
        id=f"{prefix_id}.matrix",
        title="Step 1. Pairwise Comparison Matrix",
        explanation="The pairwise comparison matrix A holds the importance comparison between elements (scale 1-9 and its reciprocals).",
        table=TableData(
            columns=["Criterion"] + labels,
            rows=step1_rows
        ),
        matrix=MatrixData(latex=f"A = {to_latex_matrix(A)}")
    )
    steps.append(step1)

    # Step 1b: Column sums
    col_sums = np.sum(A, axis=0)
    col_sum_exprs = []
    for j in range(n):
        terms = [f"{A[i, j]:.3f}" for i in range(n)]
        expr = f"{' + '.join(terms)} = {col_sums[j]:.3f}"
        col_sum_exprs.append(expr)

    step1b = Step(
        id=f"{prefix_id}.col_sums",
        title="Step 1b. Column Sums of the Matrix",
        explanation="Add up the elements of each column: s_j = \\sum_i a_{ij}.",
        table=TableData(
            columns=["Column", "Elements Summed", "Column Sum (s_j)"],
            rows=[[labels[j], col_sum_exprs[j], f"{col_sums[j]:.4f}"] for j in range(n)]
        )
    )
    steps.append(step1b)

    # Step 2: Normalisation
    Norm_A = A / col_sums
    step2_rows = []
    for i in range(n):
        row = [labels[i]]
        for j in range(n):
            row.append(f"{A[i, j]:.3f} ÷ {col_sums[j]:.3f} = {Norm_A[i, j]:.4f}")
        step2_rows.append(row)

    step2 = Step(
        id=f"{prefix_id}.normalize",
        title="Step 2. Matrix Normalisation",
        explanation="Each element is divided by the sum of its own column: n_{ij} = a_{ij} / s_j.",
        table=TableData(
            columns=["Criterion"] + labels,
            rows=step2_rows
        ),
        matrix=MatrixData(latex=f"Norm(A) = {to_latex_matrix(Norm_A)}"),
        result=ResultBox(text="Every column of the normalised matrix sums to 1.0000.", status="info")
    )
    steps.append(step2)

    # Step 3: Priority weights (approximate eigenvector)
    weights = np.mean(Norm_A, axis=1)
    step3_rows = []
    for i in range(n):
        terms = [f"{Norm_A[i, j]:.4f}" for j in range(n)]
        expr = f"({' + '.join(terms)}) ÷ {n} = {weights[i]:.4f}"
        step3_rows.append([labels[i], expr, f"{weights[i]:.4f}"])

    step3 = Step(
        id=f"{prefix_id}.weights",
        title="Step 3. Priority Weights (Weight Vector w)",
        explanation="Priority weights are the average of each row of the normalised matrix: w_i = (\\sum_j n_{ij}) / n.",
        table=TableData(
            columns=["Criterion", "Row Average Calculation", "Weight (w)"],
            rows=step3_rows
        ),
        result=ResultBox(
            text=f"Total weight: {np.sum(weights):.4f} (100%).",
            status="ok"
        )
    )
    steps.append(step3)

    # Step 4a: A · x
    Ax = np.dot(A, weights)
    step4a_rows = []
    for i in range(n):
        terms = [f"({A[i, j]:.3f} × {weights[j]:.4f})" for j in range(n)]
        expr = f"{' + '.join(terms)} = {Ax[i]:.4f}"
        step4a_rows.append([labels[i], expr, f"{Ax[i]:.4f}"])

    step4a = Step(
        id=f"{prefix_id}.ax",
        title="Step 4a. Matrix A times the Weight Vector (A · w)",
        explanation="Multiply the original comparison matrix A by the priority weight vector w.",
        table=TableData(
            columns=["Criterion", "Row A × w Product", "(A·w)_i"],
            rows=step4a_rows
        )
    )
    steps.append(step4a)

    # Step 4b: Lambda Max
    ratio = Ax / weights
    lambda_max = float(np.mean(ratio))
    step4b_rows = []
    for i in range(n):
        step4b_rows.append([labels[i], f"{Ax[i]:.4f} ÷ {weights[i]:.4f} = {ratio[i]:.4f}"])

    step4b = Step(
        id=f"{prefix_id}.lambda_max",
        title="Step 4b. Maximum Eigenvalue (λ_max)",
        explanation="Compute the ratio (A·w)_i / w_i for each element, then average them: \\lambda_{\\max} = (1/n) \\sum_i (A·w)_i / w_i.",
        table=TableData(
            columns=["Criterion", "Ratio (A·w)_i / w_i"],
            rows=step4b_rows
        ),
        result=ResultBox(text=f"Value λ_max = {lambda_max:.4f} (ideally close to n = {n}).", status="info")
    )
    steps.append(step4b)

    # Step 5: CI and CR
    if n <= 2:
        CI = 0.0
        CR = 0.0
    else:
        CI = float((lambda_max - n) / (n - 1))
        RI = RI_DICT.get(n, 1.49)
        CR = float(CI / RI) if RI > 0 else 0.0

    is_consistent = CR < 0.1
    status_box = "ok" if is_consistent else "bad"
    status_text = (
        f"CR = {CR:.4f} < 0.1 → Assessment is CONSISTENT."
        if is_consistent
        else f"CR = {CR:.4f} ≥ 0.1 → Assessment is NOT CONSISTENT! Revising the comparison values is recommended."
    )

    step5 = Step(
        id=f"{prefix_id}.consistency",
        title="Step 5. Consistency Ratio Test (CI & CR)",
        explanation=(
            f"Indeks Konsistensi: CI = (\\lambda_{{max}} - n) / (n - 1) = ({lambda_max:.4f} - {n}) / {n - 1} = {CI:.4f}.\n"
            f"Rasio Konsistensi: CR = CI / RI = {CI:.4f} / {RI_DICT.get(n, 0.0)} = {CR:.4f}."
        ),
        table=TableData(
            columns=["Parameter", "Formula / Definition", "Value"],
            rows=[
                ["Matrix Size (n)", "Number of criteria", str(n)],
                ["λ_max", "Maximum eigenvalue", f"{lambda_max:.4f}"],
                ["CI", "(λ_max - n) / (n - 1)", f"{CI:.4f}"],
                ["RI", f"Indeks acak Saaty (n={n})", f"{RI_DICT.get(n, 0.0):.2f}"],
                ["CR", "CI / RI", f"{CR:.4f}"]
            ]
        ),
        result=ResultBox(text=status_text, status=status_box)
    )
    steps.append(step5)

    # Suggested fixes when CR >= 0.1
    suggestions = []
    if n > 2 and CR >= 0.1:
        e_list = []
        for i in range(n):
            for j in range(i + 1, n):
                a_ij = A[i, j]
                ratio_w = weights[j] / weights[i]
                e_ij = a_ij * ratio_w
                # deviasi absolut logaritmik
                dev = abs(math.log(e_ij)) if e_ij > 0 else 999.0
                suggested_val = weights[i] / weights[j]
                suggested_saaty = nearest_saaty(suggested_val)
                e_list.append({
                    "pair": (labels[i], labels[j]),
                    "current": format_fraction(A_raw_str[i][j]),
                    "suggested": suggested_saaty,
                    "dev": dev
                })
        e_list.sort(key=lambda x: x["dev"], reverse=True)
        top3 = e_list[:3]
        suggestions = top3

        sug_rows = []
        for s in top3:
            sug_rows.append([
                f"{s['pair'][0]} vs {s['pair'][1]}",
                s["current"],
                s["suggested"],
                f"Change the value from {s['current']} to {s['suggested']}"
            ])
        
        step5_sug = Step(
            id=f"{prefix_id}.suggestions",
            title="Saran Perbaikan Inkonsistensi",
            explanation="Based on the deviation analysis e_{ij} = a_{ij} \\cdot (w_j / w_i), these are the pairs with the largest inconsistency and the suggested Saaty values.",
            table=TableData(
                columns=["Pair", "Current Value", "Suggested Value", "Rekomendasi"],
                rows=sug_rows
            ),
            result=ResultBox(text="Consider revising the comparison values above to lower the CR.", status="warn")
        )
        steps.append(step5_sug)

    return weights, lambda_max, CI, CR, steps, suggestions

def solve_ahp_individual(
    dm_id: str,
    criteria: List[str],
    pairwise_raw: List[List[Union[str, int, float]]],
    alternatives: List[str],
    criteria_types: Dict[str, str], # crit_id -> "benefit" | "cost"
    values: Dict[str, Dict[str, float]] # alt_id -> {crit_id: float}
) -> Tuple[ModelResult, np.ndarray, float, float, float, List[Dict[str, Any]]]:
    """
    Runs the full AHP calculation for one DM:
    - Step 1-5: Criteria weights & consistency
    - Step 6: Sub-criteria (skipped / note)
    - Step 7: Alternative weights per criterion (benefit: v / sum v, cost: (1/v) / sum(1/v))
    - Step 8: Ranking akhir AHP (P × w)
    """
    weights, lambda_max, CI, CR, steps, suggestions = calculate_ahp_weights(
        pairwise_raw=pairwise_raw,
        labels=criteria,
        prefix_id=f"ahp.{dm_id}.crit"
    )

    # Step 6: Sub-criteria (placeholder)
    step6 = Step(
        id=f"ahp.{dm_id}.subcriteria",
        title="Step 6. Sub-Criteria Weighting",
        explanation="This case uses no tiered sub-criteria; this step is skipped as in the analysis flow.",
        result=ResultBox(text="Sub-criteria are not used (skipped).", status="info")
    )
    steps.append(step6)

    # Step 7: Alternative weights per criterion
    num_alts = len(alternatives)
    num_crits = len(criteria)
    P = np.zeros((num_alts, num_crits), dtype=np.float64)

    step7_rows = []
    for j, c in enumerate(criteria):
        c_type = criteria_types[c]
        c_vals = np.array([values[a][c] for a in alternatives], dtype=np.float64)
        if c_type == "cost":
            inv_vals = 1.0 / c_vals
            sum_inv = np.sum(inv_vals)
            p_j = inv_vals / sum_inv
        else:
            sum_v = np.sum(c_vals)
            p_j = c_vals / sum_v
        P[:, j] = p_j

    for i, a in enumerate(alternatives):
        row = [a]
        for j, c in enumerate(criteria):
            row.append(f"{P[i, j]:.4f}")
        step7_rows.append(row)

    step7 = Step(
        id=f"ahp.{dm_id}.alt_weights",
        title="Step 7. Alternative Priority per Criterion (Matrix P)",
        explanation="Alternative weights are computed from the quantitative values: benefit = v_{kj} / \\sum v, cost = (1/v_{kj}) / \\sum (1/v).",
        table=TableData(
            columns=["Alternative"] + criteria,
            rows=step7_rows
        ),
        matrix=MatrixData(latex=f"P = {to_latex_matrix(P)}")
    )
    steps.append(step7)

    # Step 8: Final AHP ranking (P × w)
    ahp_scores = np.dot(P, weights)
    
    # Min ranking
    scores_dict = {a: float(ahp_scores[i]) for i, a in enumerate(alternatives)}
    from engine.ranking import rank_min
    ranks_dict = rank_min(scores_dict)
    ranks = np.array([ranks_dict[a] for a in alternatives])

    step8_rows = []
    for i, a in enumerate(alternatives):
        terms = [f"({P[i, j]:.4f} × {weights[j]:.4f})" for j in range(num_crits)]
        expr = f"{' + '.join(terms)} = {ahp_scores[i]:.4f}"
        step8_rows.append([a, expr, f"{ahp_scores[i]:.4f}", str(ranks[i])])

    # Sort the display rows of the step 8 table by rank
    step8_rows_sorted = sorted(step8_rows, key=lambda r: int(r[3]))

    step8 = Step(
        id=f"ahp.{dm_id}.final",
        title="Step 8. Final AHP Ranking",
        explanation="The final score is the priority matrix P times the criteria weight vector w: score = P \\times w.",
        table=TableData(
            columns=["Alternative", "Calculation (P × w)", "AHP Score", "Rank"],
            rows=step8_rows_sorted
        ),
        matrix=MatrixData(latex=f"P \\times w = {to_latex_matrix(ahp_scores.reshape(-1, 1))}"),
        result=ResultBox(
            text=f"AHP winner ({dm_id}): Alternative {alternatives[np.argmin(ranks)]} with score {np.max(ahp_scores):.4f}.",
            status="ok"
        )
    )
    steps.append(step8)

    # Compute each criterion's contribution per alternative: w_j * P_ij
    contributions: Dict[str, Dict[str, float]] = {}
    for i, a in enumerate(alternatives):
        contributions[a] = {}
        for j, c in enumerate(criteria):
            contributions[a][c] = round(float(weights[j] * P[i, j]), 6)

    model_result = ModelResult(
        model="AHP",
        scope="individual",
        dm_id=dm_id,
        scores=scores_dict,
        ranks=ranks_dict,
        steps=steps,
        contributions=contributions,
        meta={
            "lambda_max": lambda_max,
            "CI": CI,
            "CR": CR,
            "consistent": CR < 0.1
        }
    )

    return model_result, weights, lambda_max, CI, CR, suggestions
