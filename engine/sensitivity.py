from typing import Dict, List, Any
import numpy as np

from engine.schemas import Session, RunResult, ModelResult
from engine.borda import solve_borda_weighted
from engine.copeland import solve_copeland_group
from engine.ahp_group import solve_ahp_group_aip
from engine.ranking import find_winners

def simulate_what_if(
    result: RunResult,
    new_dm_weights: Dict[str, float]
) -> Dict[str, Any]:
    """
    Runs a What-If simulation (sensitivity analysis):
    Uses the individual ranks/scores already in the RunResult,
    then recomputes the group models (Weighted Borda, Group Copeland, Group AHP AIP)
    from the interactively chosen DM weights.
    """
    # Normalise the new weights so they sum to exactly 1.0
    tot = sum(new_dm_weights.values())
    norm_weights = {k: v / tot for k, v in new_dm_weights.items()} if tot > 0 else new_dm_weights

    alternatives = result.alternatives
    chosen_dm_rankings = {}
    dm_ahp_scores = {}

    for dm_id, indiv in result.individual.items():
        chosen_method = indiv.chosen_method.upper()
        if chosen_method in indiv.models:
            chosen_dm_rankings[dm_id] = indiv.models[chosen_method].ranks
        else:
            chosen_dm_rankings[dm_id] = indiv.models["AHP"].ranks
        
        dm_ahp_scores[dm_id] = indiv.models["AHP"].scores

    # Recompute the group models
    bw_res = solve_borda_weighted(chosen_dm_rankings, norm_weights, alternatives)
    cg_res = solve_copeland_group(chosen_dm_rankings, norm_weights, alternatives)
    aip_res = solve_ahp_group_aip(dm_ahp_scores, norm_weights, alternatives)

    simulated_group = {
        "BORDA_WEIGHTED": bw_res,
        "COPELAND_GROUP": cg_res,
        "AHP_GROUP_AIP": aip_res
    }

    winners = {
        k: find_winners(res.ranks) for k, res in simulated_group.items()
    }

    return {
        "weights": norm_weights,
        "group": simulated_group,
        "winners": winners
    }
