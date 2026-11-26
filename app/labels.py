"""Interface wording: method names, plain-language explanations and formulas. Text only, no calculation logic."""
from typing import Dict, List

# Display order of the group models (key = key in RunResult.group)
GROUP_ORDER: List[str] = [
    "AHP_GROUP_AIP",
    "SAW_GROUP",
    "TOPSIS_GROUP",
    "WP_GROUP",
    "PROFILE_MATCHING_GROUP",
    "COPELAND_GROUP",
    "BORDA_WEIGHTED",
    "BORDA_UNWEIGHTED",
]

GROUP_LABELS: Dict[str, str] = {
    "AHP_GROUP_AIP": "Group AHP",
    "SAW_GROUP": "Group SAW",
    "TOPSIS_GROUP": "Group TOPSIS",
    "WP_GROUP": "Group WP",
    "PROFILE_MATCHING_GROUP": "Group Profile Matching",
    "COPELAND_GROUP": "Group Copeland",
    "BORDA_WEIGHTED": "Weighted Borda",
    "BORDA_UNWEIGHTED": "Unweighted Borda",
}

INDIVIDUAL_LABELS: Dict[str, str] = {
    "AHP": "AHP",
    "SAW": "SAW",
    "WP": "Weighted Product",
    "TOPSIS": "TOPSIS",
    "PROFILE_MATCHING": "Profile Matching",
    "COPELAND": "Copeland",
}


# Order of the "Results by method" page
METHOD_ORDER: List[str] = ["SAW", "TOPSIS", "WP", "AHP", "PROFILE_MATCHING", "COPELAND", "BORDA"]

METHODS: Dict[str, Dict[str, str]] = {
    "SAW": {
        "label": "SAW",
        "full": "Simple Additive Weighting",
        "plain": "Each alternative's values are put on the same scale, multiplied by the criteria weights, then added up. "
                 "The easiest method to explain to a business team.",
        "group_key": "SAW_GROUP",
        "score_label": "SAW score",
        "formula": r"V_i = \sum_{j=1}^{n} w_j \cdot r_{ij} \qquad r_{ij} = \begin{cases} \frac{x_{ij}}{\max_i x_{ij}} & \text{benefit} \\ \frac{\min_i x_{ij}}{x_{ij}} & \text{cost} \end{cases}",
    },
    "TOPSIS": {
        "label": "TOPSIS",
        "full": "Technique for Order Preference by Similarity to Ideal Solution",
        "plain": "Finds the alternative closest to the ideal and farthest from the worst case "
                 "across all criteria at once.",
        "group_key": "TOPSIS_GROUP",
        "score_label": "Relative closeness",
        "formula": r"C_i^{*} = \frac{D_i^{-}}{D_i^{+} + D_i^{-}} \qquad D_i^{+} = \sqrt{\sum_j (y_{ij} - A_j^{+})^2}, \; D_i^{-} = \sqrt{\sum_j (y_{ij} - A_j^{-})^2}",
    },
    "WP": {
        "label": "Weighted Product",
        "full": "Weighted Product (WP)",
        "plain": "Similar to SAW, but values are multiplied (raised to the weight). One very bad criterion "
                 "is hard to cover up with other good ones.",
        "group_key": "WP_GROUP",
        "score_label": "Relative preference",
        "formula": r"S_i = \prod_{j=1}^{n} x_{ij}^{w_j^*} \qquad V_i = \frac{S_i}{\sum_k S_k} \qquad w_j^* = \begin{cases} +w_j & \text{benefit} \\ -w_j & \text{cost} \end{cases}",
    },
    "AHP": {
        "label": "AHP",
        "full": "Analytic Hierarchy Process",
        "plain": "Criteria weights come from the pairwise comparisons each DM fills in, then their consistency is checked. "
                 "The group version combines each DM's scores with a weighted geometric mean (AIP).",
        "group_key": "AHP_GROUP_AIP",
        "score_label": "AHP score",
        "formula": r"S_i = \sum_{j=1}^{n} w_j \cdot P_{ij} \qquad CR = \frac{\lambda_{\max} - n}{(n - 1)\,RI} \le 0.1",
    },
    "PROFILE_MATCHING": {
        "label": "Profile Matching",
        "full": "Profile Matching",
        "plain": "Each alternative is compared with a target profile. Core criteria weigh 60%, supporting criteria 40%.",
        "group_key": "PROFILE_MATCHING_GROUP",
        "score_label": "Final score",
        "formula": r"\text{GAP} = \text{Rating} - \text{Target} \qquad \text{Final score} = 60\% \cdot NCF + 40\% \cdot NSF",
    },
    "COPELAND": {
        "label": "Copeland",
        "full": "Copeland (head-to-head)",
        "plain": "A head-to-head tournament between alternatives on the weighted criteria. "
                 "The alternative with the largest wins minus losses comes first.",
        "group_key": "COPELAND_GROUP",
        "score_label": "Copeland points",
        "formula": r"M(X,Y) = \sum_{j=1}^n w_j \cdot \operatorname{sgn}(x_{j} - y_{j}) \qquad \text{Points} = \text{Wins} - \text{Losses}",
    },
    "BORDA": {
        "label": "Borda",
        "full": "Borda Count",
        "plain": "Each DM ranks the alternatives, ranks are turned into points, then the points are added up. "
                 "The weighted version gives each DM a different voting influence.",
        "group_key": "BORDA_WEIGHTED",
        "score_label": "Borda points",
        "formula": r"B_k = \sum_{i=1}^{m} v_i \cdot (m - r_{ik}) \qquad m = \text{number of alternatives}, \; r_{ik} = \text{rank of alternative } k \text{ by DM } i",
    },
}

# Saaty scale in words for the comparison slider
SAATY_WORDS: Dict[int, str] = {
    2: "slightly",
    3: "moderately",
    4: "moderately to strongly",
    5: "strongly",
    6: "strongly to very strongly",
    7: "very strongly",
    8: "almost absolutely",
    9: "absolutely",
}

CRITERION_DIRECTION: Dict[str, str] = {
    "benefit": "Higher is better",
    "cost": "Lower is better",
}


def group_label(key: str) -> str:
    return GROUP_LABELS.get(key, key)


def alt_label(alt_id: str, names: Dict[str, str]) -> str:
    return names.get(alt_id, alt_id)
