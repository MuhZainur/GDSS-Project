from datetime import datetime
import uuid
from typing import Dict, List, Any
import numpy as np

from engine.schemas import (
    Session,
    RunResult,
    DMWeightsResult,
    IndividualDMResult,
    ModelResult
)
from engine.ahp import calculate_ahp_weights, solve_ahp_individual
from engine.saw import solve_saw_individual, solve_saw_group
from engine.wp import solve_wp_individual, solve_wp_group
from engine.topsis import solve_topsis_individual, solve_topsis_group
from engine.copeland import solve_copeland_criteria, solve_copeland_group
from engine.borda import solve_borda_unweighted, solve_borda_weighted
from engine.ahp_group import solve_ahp_group_aip
from engine.profile_matching import solve_profile_matching_individual, solve_profile_matching_group
from engine.ranking import (
    find_winners,
    calculate_agreement,
    detect_close_calls
)

def run_all(session: Session, run_id: str = None) -> RunResult:
    """
    Runs the whole GDSS pipeline for the given session:
    1. DM weights (facilitator AHP or equal)
    2. Individual models per DM: AHP, SAW, WP, TOPSIS, COPELAND
    3. Group models: Borda (unweighted & weighted), Group Copeland, Group AHP (AIP)
    4. Evaluation of winners, agreement (Spearman, Kendall) and warnings (inconsistencies, ties, close calls)
    """
    if run_id is None:
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_id = f"{timestamp_str}-{uuid.uuid4().hex[:4]}"

    created_at = datetime.now().isoformat()
    alt_ids = [a.id for a in session.alternatives]
    alt_names = {a.id: a.name for a in session.alternatives}
    crit_types = {c.id: c.type for c in session.criteria}
    dm_roles = {d.id: d.role for d in session.dms}
    dm_ids = [d.id for d in session.dms]

    warnings: List[str] = []

    # 1. DM weights
    if session.dm_weighting.mode == "equal" or not session.dm_weighting.pairwise:
        equal_val = 1.0 / len(dm_ids)
        dm_weights_dict = {d: equal_val for d in dm_ids}
        dm_weights_res = DMWeightsResult(
            weights=dm_weights_dict,
            lambda_max=float(len(dm_ids)),
            CI=0.0,
            CR=0.0,
            steps=[]
        )
    else:
        order = session.dm_weighting.order if session.dm_weighting.order else dm_ids
        w_dm, l_max_dm, ci_dm, cr_dm, steps_dm, _ = calculate_ahp_weights(
            pairwise_raw=session.dm_weighting.pairwise,
            labels=order,
            prefix_id="ahp.facilitator.dm"
        )
        dm_weights_dict = {d: float(w_dm[i]) for i, d in enumerate(order)}
        dm_weights_res = DMWeightsResult(
            weights=dm_weights_dict,
            lambda_max=l_max_dm,
            CI=ci_dm,
            CR=cr_dm,
            steps=steps_dm
        )
        if cr_dm >= 0.1:
            warnings.append(f"The DM weights (Facilitator) are not consistent, CR = {cr_dm:.4f} ≥ 0.1.")

    # 2. Model Individu per DM
    individual_results: Dict[str, IndividualDMResult] = {}
    chosen_dm_rankings: Dict[str, Dict[str, int]] = {}
    dm_ahp_scores: Dict[str, Dict[str, float]] = {}
    dm_saw_scores: Dict[str, Dict[str, float]] = {}
    dm_wp_scores: Dict[str, Dict[str, float]] = {}
    dm_topsis_scores: Dict[str, Dict[str, float]] = {}
    dm_pm_scores: Dict[str, Dict[str, float]] = {}

    for dm_id in dm_ids:
        dm_in = session.dm_inputs[dm_id]
        role = dm_roles.get(dm_id, dm_id)

        # Compute the individual AHP (criteria weights are computed first)
        ahp_res, crit_weights, l_max, ci, cr, sug = solve_ahp_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            pairwise_raw=dm_in.pairwise,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )

        crit_weights_dict = {c: float(crit_weights[j]) for j, c in enumerate(dm_in.criteria)}
        dm_ahp_scores[dm_id] = ahp_res.scores

        if cr >= 0.1:
            warnings.append(f"{dm_id} ({role}) has inconsistent criteria comparisons (CR = {cr:.4f} ≥ 0.1).")

        # Compute the individual SAW with the AHP weights
        saw_res = solve_saw_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            criteria_weights=crit_weights,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )
        dm_saw_scores[dm_id] = saw_res.scores

        # Compute the individual WP with the AHP weights
        wp_res = solve_wp_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            criteria_weights=crit_weights,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )
        dm_wp_scores[dm_id] = wp_res.scores

        # Compute the individual TOPSIS with the AHP weights
        topsis_res = solve_topsis_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            criteria_weights=crit_weights,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )
        dm_topsis_scores[dm_id] = topsis_res.scores

        # Compute the individual Copeland with the AHP weights
        copeland_res = solve_copeland_criteria(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            criteria_weights=crit_weights,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )

        # Compute the individual Profile Matching with the AHP weights
        pm_res = solve_profile_matching_individual(
            dm_id=dm_id,
            criteria=dm_in.criteria,
            criteria_weights=crit_weights,
            alternatives=alt_ids,
            criteria_types=crit_types,
            values=session.values
        )
        dm_pm_scores[dm_id] = pm_res.scores

        dm_models = {
            "AHP": ahp_res,
            "SAW": saw_res,
            "WP": wp_res,
            "TOPSIS": topsis_res,
            "COPELAND": copeland_res,
            "PROFILE_MATCHING": pm_res
        }

        # Store the rank of the DM's reference model
        chosen_method = dm_in.chosen_method.upper()
        if chosen_method not in dm_models:
            chosen_method = "AHP"

        chosen_dm_rankings[dm_id] = dm_models[chosen_method].ranks

        individual_results[dm_id] = IndividualDMResult(
            role=role,
            criteria=dm_in.criteria,
            criteria_weights=crit_weights_dict,
            consistency={
                "lambda_max": l_max,
                "CI": ci,
                "CR": cr,
                "consistent": cr < 0.1,
                "suggestions": sug
            },
            chosen_method=chosen_method,
            models=dm_models
        )

    # 3. Group models (the GDSS has its own ranking for every method)
    borda_unweighted = solve_borda_unweighted(
        dm_rankings=chosen_dm_rankings,
        alternatives=alt_ids
    )

    borda_weighted = solve_borda_weighted(
        dm_rankings=chosen_dm_rankings,
        dm_weights=dm_weights_dict,
        alternatives=alt_ids
    )

    copeland_group = solve_copeland_group(
        dm_rankings=chosen_dm_rankings,
        dm_weights=dm_weights_dict,
        alternatives=alt_ids
    )

    ahp_group_aip = solve_ahp_group_aip(
        dm_ahp_scores=dm_ahp_scores,
        dm_weights=dm_weights_dict,
        alternatives=alt_ids
    )

    saw_group = solve_saw_group(
        dm_saw_scores=dm_saw_scores,
        dm_weights=dm_weights_dict,
        alternatives=alt_ids
    )

    wp_group = solve_wp_group(
        dm_wp_scores=dm_wp_scores,
        dm_weights=dm_weights_dict,
        alternatives=alt_ids
    )

    topsis_group = solve_topsis_group(
        dm_topsis_scores=dm_topsis_scores,
        dm_weights=dm_weights_dict,
        alternatives=alt_ids
    )

    pm_group = solve_profile_matching_group(
        dm_pm_scores=dm_pm_scores,
        dm_weights=dm_weights_dict,
        alternatives=alt_ids
    )

    group_results: Dict[str, ModelResult] = {
        "BORDA_WEIGHTED": borda_weighted,
        "BORDA_UNWEIGHTED": borda_unweighted,
        "COPELAND_GROUP": copeland_group,
        "AHP_GROUP_AIP": ahp_group_aip,
        "SAW_GROUP": saw_group,
        "WP_GROUP": wp_group,
        "TOPSIS_GROUP": topsis_group,
        "PROFILE_MATCHING_GROUP": pm_group
    }

    # 4. Winners
    winners: Dict[str, List[str]] = {}
    for g_key, g_res in group_results.items():
        winners[g_key] = find_winners(g_res.ranks)

    # 5. Agreement between the group models
    group_ranks = {k: res.ranks for k, res in group_results.items()}
    spearman_map, kendall_map = calculate_agreement(group_ranks, alt_ids)
    agreement = {
        "spearman": spearman_map,
        "kendall": kendall_map
    }

    # Detect close calls in the group models
    for g_key, g_res in group_results.items():
        c_calls = detect_close_calls(g_res.scores, g_res.ranks)
        for cc in c_calls:
            warnings.append(f"Close call in {g_key}: {cc['a']} vs {cc['b']} (gap = {cc['gap']:.6f}).")

    return RunResult(
        run_id=run_id,
        session_id=session.session_id,
        created_at=created_at,
        app_version="0.1.0",
        alternatives=alt_ids,
        alternative_names=alt_names,
        dm_weights=dm_weights_res,
        individual=individual_results,
        group=group_results,
        agreement=agreement,
        winners=winners,
        warnings=warnings
    )
