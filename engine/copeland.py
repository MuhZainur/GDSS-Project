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

def solve_copeland_criteria(
    dm_id: str,
    criteria: List[str],
    criteria_weights: np.ndarray,
    alternatives: List[str],
    criteria_types: Dict[str, str], # crit_id -> "benefit" | "cost"
    values: Dict[str, Dict[str, float]] # alt_id -> {crit_id: float}
) -> ModelResult:
    """
    Solves Criteria Copeland (individual model per DM).
    Every alternative is compared one-on-one (head-to-head).
    The criteria weights are added up for the alternative that is better.
    """
    num_alts = len(alternatives)
    w = {c: float(criteria_weights[j]) for j, c in enumerate(criteria)}

    steps: List[Step] = []

    # Step 1: Criteria and weights table
    step1_rows = []
    for c in criteria:
        step1_rows.append([c, criteria_types[c], f"{w[c]:.4f}"])
    steps.append(Step(
        id=f"copeland.{dm_id}.data",
        title="Step 1. Criteria and AHP Weights",
        explanation="The criteria used, with their type and the priority weights from AHP.",
        table=TableData(
            columns=["Criterion", "Tipe", "Weight (w)"],
            rows=step1_rows
        )
    ))

    # Step 2: Order per criterion
    step2_rows = []
    for c in criteria:
        c_type = criteria_types[c]
        # Urutkan: benefit desc, cost asc
        is_benefit = (c_type == "benefit")
        sorted_alts = sorted(alternatives, key=lambda a: values[a][c], reverse=is_benefit)
        order_str = " > ".join([f"{a} ({values[a][c]})" for a in sorted_alts])
        step2_rows.append([c, c_type, order_str])

    steps.append(Step(
        id=f"copeland.{dm_id}.order",
        title="Step 2. Urutan Alternative per Criterion",
        explanation="Benefit criteria are ordered from largest; cost criteria from smallest.",
        table=TableData(
            columns=["Criterion", "Tipe", "Order of Alternatives (Best → Worst)"],
            rows=step2_rows
        )
    ))

    # Step 3: Pairwise contests (head-to-head)
    # Contest matrix: cell (i, j) = +1 if i beats j, -1 if it loses, 0 if tied
    match_matrix = np.zeros((num_alts, num_alts), dtype=int)
    wins = {a: 0 for a in alternatives}
    losses = {a: 0 for a in alternatives}
    ties = {a: 0 for a in alternatives}
    contests = []

    for i in range(num_alts):
        for j in range(i + 1, num_alts):
            alt_a = alternatives[i]
            alt_b = alternatives[j]

            weight_a = 0.0
            weight_b = 0.0
            criteria_a = []
            criteria_b = []

            for c in criteria:
                val_a = values[alt_a][c]
                val_b = values[alt_b][c]
                c_type = criteria_types[c]

                if abs(val_a - val_b) < 1e-12:
                    # Equal values -> nobody gets the weight
                    continue

                if c_type == "benefit":
                    if val_a > val_b:
                        weight_a += w[c]
                        criteria_a.append(c)
                    else:
                        weight_b += w[c]
                        criteria_b.append(c)
                else: # cost
                    if val_a < val_b:
                        weight_a += w[c]
                        criteria_a.append(c)
                    else:
                        weight_b += w[c]
                        criteria_b.append(c)

            # Decide the winner
            if weight_a > weight_b + 1e-12:
                match_matrix[i, j] = 1
                match_matrix[j, i] = -1
                wins[alt_a] += 1
                losses[alt_b] += 1
                winner = alt_a
                res_desc = f"{alt_a} wins ({weight_a:.4f} vs {weight_b:.4f})"
            elif weight_b > weight_a + 1e-12:
                match_matrix[i, j] = -1
                match_matrix[j, i] = 1
                wins[alt_b] += 1
                losses[alt_a] += 1
                winner = alt_b
                res_desc = f"{alt_b} wins ({weight_b:.4f} vs {weight_a:.4f})"
            else:
                match_matrix[i, j] = 0
                match_matrix[j, i] = 0
                ties[alt_a] += 1
                ties[alt_b] += 1
                winner = "Tie"
                res_desc = f"Tie ({weight_a:.4f} vs {weight_b:.4f})"

            contests.append({
                "pair": f"{alt_a} vs {alt_b}",
                "a": alt_a,
                "b": alt_b,
                "weight_a": round(weight_a, 4),
                "weight_b": round(weight_b, 4),
                "winner": winner,
                "desc": res_desc
            })

    # Contest summary table
    step3_rows = []
    for c in contests:
        step3_rows.append([c["pair"], f"{c['weight_a']:.4f}", f"{c['weight_b']:.4f}", c["winner"], c["desc"]])

    steps.append(Step(
        id=f"copeland.{dm_id}.contests",
        title="Step 3. One-on-One Contests (Head-to-head)",
        explanation="For each pair of alternatives, the weights of the criteria on which an alternative wins are added up. The alternative with the larger total weight gets +1 (win) and its opponent gets -1 (loss).",
        table=TableData(
            columns=["Contest", "Alternative 1 Weight", "Alternative 2 Weight", "Winner", "Note"],
            rows=step3_rows
        )
    ))

    # 7x7 contest matrix
    matrix_rows = []
    for i, a in enumerate(alternatives):
        row = [a]
        for j in range(num_alts):
            if i == j:
                row.append("-")
            elif match_matrix[i, j] == 1:
                row.append("+1 (W)")
            elif match_matrix[i, j] == -1:
                row.append("-1 (L)")
            else:
                row.append("0 (T)")
        matrix_rows.append(row)

    steps.append(Step(
        id=f"copeland.{dm_id}.matrix",
        title="Step 3b. Contest Result Matrix",
        explanation="W = Win (+1), L = Loss (-1), T = Tie (0). Each row is the alternative competing against the column.",
        table=TableData(
            columns=["Alternative"] + alternatives,
            rows=matrix_rows
        )
    ))

    # Step 4: Copeland points
    scores = {}
    step4_rows = []
    for a in alternatives:
        point = float(wins[a] - losses[a])
        scores[a] = point
        step4_rows.append([a, str(wins[a]), str(ties[a]), str(losses[a]), f"{point:.0f}"])

    steps.append(Step(
        id=f"copeland.{dm_id}.points",
        title="Step 4. Copeland Points Summary",
        explanation="Copeland points = number of wins - number of losses.",
        table=TableData(
            columns=["Alternative", "Wins (W)", "Ties (T)", "Losses (L)", "Copeland Points (W - L)"],
            rows=step4_rows
        )
    ))

    # Step 5: Ranking
    ranks = rank_min(scores)
    step5_rows = []
    for a in alternatives:
        step5_rows.append([a, f"{scores[a]:.0f}", str(ranks[a])])
    step5_rows_sorted = sorted(step5_rows, key=lambda r: int(r[2]))

    steps.append(Step(
        id=f"copeland.{dm_id}.rank",
        title="Step 5. Final Criteria Copeland Ranking",
        explanation="Alternatives are ordered from the highest to the lowest Copeland points.",
        table=TableData(
            columns=["Alternative", "Copeland Points", "Rank"],
            rows=step5_rows_sorted
        ),
        result=ResultBox(
            text=f"Winner Copeland ({dm_id}): Alternative {step5_rows_sorted[0][0]} with points {step5_rows_sorted[0][1]}.",
            status="ok"
        )
    ))

    return ModelResult(
        model="COPELAND",
        scope="individual",
        dm_id=dm_id,
        scores=scores,
        ranks=ranks,
        steps=steps,
        extra={
            "wins": wins,
            "ties": ties,
            "losses": losses,
            "contests": contests,
            "match_matrix": match_matrix.tolist()
        }
    )

def solve_copeland_group(
    dm_rankings: Dict[str, Dict[str, int]], # dm_id -> {alt_id: rank}
    dm_weights: Dict[str, float], # dm_id -> weight
    alternatives: List[str]
) -> ModelResult:
    """
    Solves Group Copeland:
    - Criteria are replaced by DMs
    - Criteria weights are replaced by the DM importance weights (from the AHP between DMs)
    - Alternative values are replaced by the rank from the DM's reference model (smaller rank = more baik)
    """
    num_alts = len(alternatives)
    dms = list(dm_weights.keys())

    steps: List[Step] = []

    # Step 1: Collect the DM ranks and weights
    step1_rows = []
    for d in dms:
        row = [d, f"{dm_weights[d]:.4f}"]
        for a in alternatives:
            row.append(str(dm_rankings[d].get(a, "-")))
        step1_rows.append(row)

    steps.append(Step(
        id="copeland.group.input",
        title="Step 1. Decision Maker (DM) Ranks and Weights",
        explanation="Each DM has a weight from the AHP between DMs and provides the alternative ranking of their reference model.",
        table=TableData(
            columns=["DM", "Weight (v)"] + alternatives,
            rows=step1_rows
        )
    ))

    # Step 2: Pairwise contests (head-to-head)
    match_matrix = np.zeros((num_alts, num_alts), dtype=int)
    wins = {a: 0 for a in alternatives}
    losses = {a: 0 for a in alternatives}
    ties = {a: 0 for a in alternatives}
    contests = []

    for i in range(num_alts):
        for j in range(i + 1, num_alts):
            alt_a = alternatives[i]
            alt_b = alternatives[j]

            weight_a = 0.0
            weight_b = 0.0

            for d in dms:
                r_a = dm_rankings[d][alt_a]
                r_b = dm_rankings[d][alt_b]
                v = dm_weights[d]

                # smaller rank = preferred
                if r_a < r_b:
                    weight_a += v
                elif r_b < r_a:
                    weight_b += v
                # If equal, no weight is added

            if weight_a > weight_b + 1e-12:
                match_matrix[i, j] = 1
                match_matrix[j, i] = -1
                wins[alt_a] += 1
                losses[alt_b] += 1
                winner = alt_a
                desc = f"{alt_a} wins ({weight_a:.4f} vs {weight_b:.4f})"
            elif weight_b > weight_a + 1e-12:
                match_matrix[i, j] = -1
                match_matrix[j, i] = 1
                wins[alt_b] += 1
                losses[alt_a] += 1
                winner = alt_b
                desc = f"{alt_b} wins ({weight_b:.4f} vs {weight_a:.4f})"
            else:
                match_matrix[i, j] = 0
                match_matrix[j, i] = 0
                ties[alt_a] += 1
                ties[alt_b] += 1
                winner = "Tie"
                desc = f"Tie ({weight_a:.4f} vs {weight_b:.4f})"

            contests.append({
                "pair": f"{alt_a} vs {alt_b}",
                "a": alt_a,
                "b": alt_b,
                "weight_a": round(weight_a, 4),
                "weight_b": round(weight_b, 4),
                "winner": winner,
                "desc": desc
            })

    step2_rows = []
    for c in contests:
        step2_rows.append([c["pair"], f"{c['weight_a']:.4f}", f"{c['weight_b']:.4f}", c["winner"], c["desc"]])

    steps.append(Step(
        id="copeland.group.contests",
        title="Step 2. Head-to-Head Contests Between Alternatives (Group Level)",
        explanation="For each pair of alternatives, the weights of the DMs who prefer that alternative are added up.",
        table=TableData(
            columns=["Contest", "Alternative 1 Vote Weight", "Alternative 2 Vote Weight", "Winner", "Note"],
            rows=step2_rows
        )
    ))

    # 7x7 contest matrix
    matrix_rows = []
    for i, a in enumerate(alternatives):
        row = [a]
        for j in range(num_alts):
            if i == j:
                row.append("-")
            elif match_matrix[i, j] == 1:
                row.append("+1 (W)")
            elif match_matrix[i, j] == -1:
                row.append("-1 (L)")
            else:
                row.append("0 (T)")
        matrix_rows.append(row)

    steps.append(Step(
        id="copeland.group.matrix",
        title="Step 2b. Group Contest Result Matrix",
        explanation="The one-on-one comparison matrix between alternatives at group level.",
        table=TableData(
            columns=["Alternative"] + alternatives,
            rows=matrix_rows
        )
    ))

    # Points summary
    scores = {}
    step3_rows = []
    for a in alternatives:
        point = float(wins[a] - losses[a])
        scores[a] = point
        step3_rows.append([a, str(wins[a]), str(ties[a]), str(losses[a]), f"{point:.0f}"])

    steps.append(Step(
        id="copeland.group.points",
        title="Step 3. Group Copeland Points Summary",
        explanation="Copeland points = wins - losses.",
        table=TableData(
            columns=["Alternative", "Wins (W)", "Ties (T)", "Losses (L)", "Copeland Points (W - L)"],
            rows=step3_rows
        )
    ))

    # Ranking
    ranks = rank_min(scores)
    step4_rows = []
    for a in alternatives:
        step4_rows.append([a, f"{scores[a]:.0f}", str(ranks[a])])
    step4_rows_sorted = sorted(step4_rows, key=lambda r: int(r[2]))

    steps.append(Step(
        id="copeland.group.rank",
        title="Step 4. Final Group Copeland Ranking",
        explanation="Alternatives are ordered from the largest to the smallest group Copeland points.",
        table=TableData(
            columns=["Alternative", "Copeland Points", "Rank"],
            rows=step4_rows_sorted
        ),
        result=ResultBox(
            text=f"Group Copeland winner: Alternative {step4_rows_sorted[0][0]} with points {step4_rows_sorted[0][1]}.",
            status="ok"
        )
    ))

    return ModelResult(
        model="COPELAND_GROUP",
        scope="group",
        scores=scores,
        ranks=ranks,
        steps=steps,
        extra={
            "wins": wins,
            "ties": ties,
            "losses": losses,
            "contests": contests,
            "match_matrix": match_matrix.tolist()
        }
    )
