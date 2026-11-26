import math
from typing import Dict, List, Tuple, Any

def rank_min(scores: Dict[str, float]) -> Dict[str, int]:
    """
    Computes ranks with the 'min' method (larger score = smaller/better rank).
    If scores are equal (difference < 1e-9), the ranks are equal (for example 1, 1, 3).
    """
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ranks: Dict[str, int] = {}
    for idx, (alt, score) in enumerate(sorted_items):
        if idx > 0 and abs(score - sorted_items[idx - 1][1]) < 1e-9:
            ranks[alt] = ranks[sorted_items[idx - 1][0]]
        else:
            ranks[alt] = idx + 1
    return ranks

def find_winners(ranks: Dict[str, int]) -> List[str]:
    """Returns the ids of the alternatives ranked 1 (several when tied)."""
    min_r = min(ranks.values())
    return [alt for alt, r in ranks.items() if r == min_r]

def compute_spearman(r1: List[float], r2: List[float]) -> float:
    """Computes the Spearman correlation coefficient between two rank vectors."""
    try:
        from scipy.stats import spearmanr
        corr, _ = spearmanr(r1, r2)
        if math.isnan(corr):
            return 1.0
        return float(corr)
    except Exception:
        # Fallback pure python
        n = len(r1)
        if n == 0:
            return 1.0
        d_sq = sum((a - b) ** 2 for a, b in zip(r1, r2))
        return float(1.0 - (6.0 * d_sq) / (n * (n * n - 1)))

def compute_kendall(r1: List[float], r2: List[float]) -> float:
    """Computes the Kendall tau correlation coefficient between two rank vectors."""
    try:
        from scipy.stats import kendalltau
        corr, _ = kendalltau(r1, r2)
        if math.isnan(corr):
            return 1.0
        return float(corr)
    except Exception:
        # Fallback pure python tau-b
        n = len(r1)
        concordant = 0
        discordant = 0
        for i in range(n):
            for j in range(i + 1, n):
                s = (r1[i] - r1[j]) * (r2[i] - r2[j])
                if s > 0:
                    concordant += 1
                elif s < 0:
                    discordant += 1
        denom = (n * (n - 1)) / 2.0
        return float((concordant - discordant) / denom) if denom > 0 else 1.0

def calculate_agreement(models_ranks: Dict[str, Dict[str, int]], alternatives: List[str]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Computes the Spearman and Kendall tau correlation matrices between pairs of models.
    """
    model_keys = list(models_ranks.keys())
    spearman_dict = {}
    kendall_dict = {}
    
    for i in range(len(model_keys)):
        for j in range(i + 1, len(model_keys)):
            m1 = model_keys[i]
            m2 = model_keys[j]
            r1 = [float(models_ranks[m1].get(a, 0)) for a in alternatives]
            r2 = [float(models_ranks[m2].get(a, 0)) for a in alternatives]
            
            pair_key = f"{m1}|{m2}"
            spearman_dict[pair_key] = round(compute_spearman(r1, r2), 4)
            kendall_dict[pair_key] = round(compute_kendall(r1, r2), 4)
            
    return spearman_dict, kendall_dict

def detect_close_calls(scores: Dict[str, float], ranks: Dict[str, int]) -> List[Dict[str, Any]]:
    """
    Detects consecutive ranked pairs whose score gap is < 1% of that model's maximum score.
    """
    max_score = max(scores.values()) if scores else 1.0
    threshold = 0.01 * max_score
    sorted_by_rank = sorted(ranks.items(), key=lambda x: x[1])
    
    close_calls = []
    for i in range(len(sorted_by_rank) - 1):
        alt_a, rank_a = sorted_by_rank[i]
        alt_b, rank_b = sorted_by_rank[i + 1]
        gap = abs(scores[alt_a] - scores[alt_b])
        if gap < threshold:
            close_calls.append({
                "a": alt_a,
                "b": alt_b,
                "rank_a": rank_a,
                "rank_b": rank_b,
                "gap": round(float(gap), 6)
            })
    return close_calls
