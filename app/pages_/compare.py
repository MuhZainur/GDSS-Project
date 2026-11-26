"""Page 5: Comparison across methods, vote-weight scenarios and downloads."""
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from app.components.charts import (
    chart_agreement_heatmap,
    chart_average_rank,
    chart_bump,
    chart_group_rank_heatmap,
    chart_radar_criteria_profile,
    chart_rank_heatmap,
    chart_weights_bar,
)
from app.insights import consensus, group_keys, top_alts
from app.labels import GROUP_LABELS, group_label
from app.pages_.common import need_run
from app.repository import export_rankings_csv
from app.theme import callout, chip, esc, page_header, render_html, section, show_chart
from engine.schemas import RunResult, Session
from engine.sensitivity import simulate_what_if

WHATIF_MODELS = ["BORDA_WEIGHTED", "COPELAND_GROUP", "AHP_GROUP_AIP"]


def _reset_whatif(result: RunResult) -> None:
    for dm_id, w in result.dm_weights.weights.items():
        st.session_state[f"wi_{dm_id}"] = int(round(w * 100))


def _radar_matrix(session: Session, alts) -> pd.DataFrame:
    """Criteria values on one scale (1 = best), with the benefit/cost direction taken into account."""
    mat: Dict[str, Dict[str, float]] = {a: {} for a in alts}
    for c in session.criteria:
        vals = [session.values.get(a, {}).get(c.id, 1.0) for a in alts]
        hi, lo = max(vals), min(vals)
        for a in alts:
            v = session.values.get(a, {}).get(c.id, 1.0)
            if c.type.lower() == "benefit":
                mat[a][c.id] = v / hi if hi > 0 else 0
            else:
                mat[a][c.id] = lo / v if v > 0 else 0
    return pd.DataFrame(mat).T


def render(result: Optional[RunResult], session: Session) -> None:
    page_header(
        "Comparison across methods",
        "Do all the methods agree? Here you can see where each product stands in every method, and how strong the agreement is.",
    )
    if result is None:
        need_run("perbandingan", "the comparison")
        return

    names = result.alternative_names
    cons = consensus(result)
    best = cons["best"]
    keys = group_keys(result)

    # ── Rank in every method ───────────────────────────────────────────
    section("Rank of each product in each method", "dark = good rank, number = rank")
    show_chart(chart_group_rank_heatmap(result, names), key="cmp_heat")

    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        show_chart(chart_average_rank(cons["table"]["avg_rank"], best, names), key="cmp_avg")
    with col_b:
        if session.criteria:
            norm = _radar_matrix(session, result.alternatives)
            show_chart(
                chart_radar_criteria_profile(norm, [c.id for c in session.criteria], names, best),
                key="cmp_radar",
            )

    show_chart(chart_bump(result, names), key="cmp_bump")

    # ── Agreement ─────────────────────────────────────────────────────────
    section("How similar the orderings of the methods are")
    show_chart(chart_agreement_heatmap(result), key="cmp_agree")
    st.caption("A number close to 1 means two methods order the products almost the same way. Close to 0 means the orderings are unrelated.")

    # ── Vote-weight scenario ────────────────────────────────────────────────
    section("Scenario test: what if the DMs' vote weights change?", "only recalculates the group aggregation")
    dm_ids = list(result.individual.keys())
    if st.session_state.get("wi_run") != result.run_id:  # new run: the sliders go back to that run's weights
        _reset_whatif(result)
        st.session_state["wi_run"] = result.run_id

    cols = st.columns(len(dm_ids))
    new_w: Dict[str, float] = {}
    for col, dm_id in zip(cols, dm_ids):
        with col:
            new_w[dm_id] = float(
                st.slider(
                    f"{dm_id} · {result.individual[dm_id].role}",
                    min_value=0,
                    max_value=100,
                    step=1,
                    key=f"wi_{dm_id}",
                )
            )
    st.button("Reset to the original weights", on_click=_reset_whatif, args=(result,), key="wi_reset")

    if sum(new_w.values()) <= 0:
        callout("warn", "Give a weight above 0 to at least one DM.")
    else:
        sim = simulate_what_if(result, new_w)
        tot = sum(new_w.values())
        render_html(
            '<div class="step-note">Weights used after normalising: '
            + ", ".join(f"{d} {w / tot * 100:.0f}%" for d, w in new_w.items())
            + "</div>"
        )
        body = ""
        n_changed = 0
        for k in WHATIF_MODELS:
            base = top_alts(result.group[k].ranks) if k in result.group else []
            now = sim["winners"].get(k, [])
            changed = set(base) != set(now)
            n_changed += int(changed)
            order = sorted(sim["group"][k].ranks.items(), key=lambda kv: kv[1])
            order_txt = " › ".join(names.get(a, a) for a, _ in order[:3])
            body += (
                f"<tr><td><b>{esc(group_label(k))}</b></td>"
                f'<td>{esc(" / ".join(names.get(a, a) for a in base))}</td>'
                f'<td><b>{esc(" / ".join(names.get(a, a) for a in now))}</b></td>'
                f'<td>{chip("Changed", "warn") if changed else chip("Unchanged", "ok")}</td>'
                f'<td class="sub">{esc(order_txt)}</td></tr>'
            )
        render_html(
            '<table class="tbl"><thead><tr><th>Group method</th><th>Original winner</th><th>Scenario winner</th><th>Status</th><th>Top three (scenario)</th></tr></thead><tbody>',
            body,
            "</tbody></table>",
        )
        if n_changed == 0:
            callout("ok", "The winner does not change in this scenario. The recommendation is fairly robust to vote weights.")
        else:
            callout("warn", f"The winner changes in {n_changed} of {len(WHATIF_MODELS)} methods. The recommendation is sensitive to the DMs' vote weights.")

    # ── Extra detail ────────────────────────────────────────────────────
    section("Extra detail")
    crit_names = {c.id: c.name for c in session.criteria}
    with st.expander("What each DM emphasises (criteria weights)"):
        show_chart(chart_weights_bar(result, names, crit_names), key="cmp_weights")
    with st.expander("Rank in every method, for each DM and the group"):
        show_chart(chart_rank_heatmap(result, names), key="cmp_heat_full")
    with st.expander("Group score and rank table"):
        data = {"Product": [f"{a} · {names.get(a, a)}" for a in result.alternatives]}
        for k in keys:
            data[f"Score {GROUP_LABELS.get(k, k)}"] = [result.group[k].scores.get(a, 0.0) for a in result.alternatives]
            data[f"Rank {GROUP_LABELS.get(k, k)}"] = [int(result.group[k].ranks.get(a, 0)) for a in result.alternatives]
        st.dataframe(pd.DataFrame(data).style.format({c: "{:.4f}" for c in data if c.startswith("Score")}), hide_index=True, width="stretch")

    # ── Download ───────────────────────────────────────────────────────────────
    section("Download results")
    d1, d2, _ = st.columns([1.4, 1.4, 3])
    d1.download_button(
        "Rankings (CSV)",
        data=export_rankings_csv(result),
        file_name=f"rankings_{result.run_id}.csv",
        mime="text/csv",
        key="dl_csv",
        width="stretch",
    )
    d2.download_button(
        "Full results (JSON)",
        data=result.model_dump_json(indent=2),
        file_name=f"results_{result.run_id}.json",
        mime="application/json",
        key="dl_json",
        width="stretch",
    )
