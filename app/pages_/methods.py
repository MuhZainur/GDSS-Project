"""Page 4: Results by method. One generic page for every method, not one tab per method."""
from typing import Callable, Dict, List, Optional

import pandas as pd
import streamlit as st

from app.components.charts import (
    chart_copeland_matrix,
    chart_stacked_borda_contributions,
    chart_stacked_contributions,
    chart_topsis_scatter,
    ranked_bar,
)
from app.components.step_renderer import render_step
from app.insights import top_alts
from app.labels import METHOD_ORDER, METHODS
from app.pages_.common import need_run
from app.theme import ACCENT_SOFT, callout, chip, esc, page_header, render_html, section, show_chart
from engine.schemas import IndividualDMResult, ModelResult, RunResult, Session


# ── Result table ──────────────────────────────────────────────────────────────
def _fmt_score(values: List[float]) -> Callable[[float], str]:
    if all(float(v).is_integer() for v in values):
        return lambda v: f"{v:.0f}"
    return lambda v: f"{v:.4f}"


def _result_table(
    res: ModelResult,
    names: Dict[str, str],
    score_label: str,
    extra: Optional[Dict[str, Dict[str, float]]] = None,
    extra_fmt: Optional[Dict[str, str]] = None,
) -> None:
    alts = list(res.scores.keys())
    data = {
        "Rank": [int(res.ranks.get(a, 0)) for a in alts],
        "Product": [f"{a} · {names.get(a, a)}" for a in alts],
        score_label: [float(res.scores[a]) for a in alts],
    }
    for col, series in (extra or {}).items():
        data[col] = [series.get(a, 0) for a in alts]
    df = pd.DataFrame(data).sort_values("Rank", kind="stable").reset_index(drop=True)

    fmt = {score_label: _fmt_score(list(df[score_label]))}
    for col, f in (extra_fmt or {}).items():
        fmt[col] = f

    def hl(row: pd.Series):
        return [f"background-color:{ACCENT_SOFT}" if row["Rank"] == 1 else ""] * len(row)

    st.dataframe(
        df.style.apply(hl, axis=1).format(fmt),
        hide_index=True,
        width="stretch",
        height=35 * (len(df) + 1) + 3,
    )


def _winner_callout(res: ModelResult, names: Dict[str, str], who: str, score_label: str) -> List[str]:
    wins = top_alts(res.ranks)
    label = " / ".join(f"{names.get(a, a)} ({a})" for a in wins)
    score = res.scores[wins[0]] if wins else 0.0
    shown = f"{score:.0f}" if float(score).is_integer() else f"{score:.4f}"
    callout("accent", f"{label}. {score_label}: {shown}", f"Winner: {who}")
    return wins


def _steps(res: ModelResult, title: str) -> None:
    if res.steps:
        with st.expander(f"{title} ({len(res.steps)} steps)"):
            for s in res.steps:
                render_step(s)


# ── Per method ───────────────────────────────────────────────────────────────
def _group_view(method: str, result: RunResult, names: Dict[str, str]) -> None:
    meta = METHODS[method]
    res = result.group.get(meta["group_key"])
    if res is None:
        callout("warn", "The group result for this method is not in the loaded run.")
        return
    _winner_callout(res, names, "group consensus", meta["score_label"])

    extra = None
    extra_fmt = None
    if method == "COPELAND" and res.extra:
        extra = {"Wins": res.extra.get("wins", {}), "Ties": res.extra.get("ties", {}), "Losses": res.extra.get("losses", {})}
        extra_fmt = {k: "{:.0f}" for k in extra}
    _result_table(res, names, meta["score_label"], extra, extra_fmt)

    winner = (top_alts(res.ranks) or [""])[0]
    show_chart(
        ranked_bar(pd.Series(res.scores), names, winner, meta["score_label"], f"{meta['label']} group"),
        key=f"met_grp_bar_{method}",
    )
    if method == "COPELAND":
        fig = chart_copeland_matrix(result, names, model_key="COPELAND_GROUP")
        if fig:
            show_chart(fig, key="met_grp_cop")
    _steps(res, "Group calculation trace")


def _individual_view(method: str, dm_id: str, result: RunResult, names: Dict[str, str], session: Session) -> None:
    meta = METHODS[method]
    indiv: IndividualDMResult = result.individual[dm_id]
    res = indiv.models.get(method)
    if res is None:
        callout("warn", f"Method {meta['label']} was not found for {dm_id}.")
        return

    crit_names = {c.id: c.name for c in session.criteria}
    crit_types = {c.id: c.type.lower() for c in session.criteria}

    render_html(
        f'<div style="margin:0.2rem 0 0.6rem"><b>{esc(indiv.role)}</b> '
        + chip(f"{len(indiv.criteria)} criteria")
        + "</div>"
    )
    weights_txt = ", ".join(
        f"{crit_names.get(c, c)} {w * 100:.0f}%"
        for c, w in sorted(indiv.criteria_weights.items(), key=lambda kv: kv[1], reverse=True)
    )
    st.caption(f"Criteria weights of {indiv.role}: {weights_txt}")

    _winner_callout(res, names, f"{indiv.role} ({dm_id})", meta["score_label"])

    extra: Dict[str, Dict[str, float]] = {}
    extra_fmt: Dict[str, str] = {}
    ex = res.extra or {}
    if method == "TOPSIS":
        extra = {"Distance to ideal (D+)": ex.get("d_plus", {}), "Distance to worst (D−)": ex.get("d_minus", {})}
        extra_fmt = {k: "{:.4f}" for k in extra}
    elif method == "WP":
        # V_i = S_i / ΣS, so S_i = V_i × ΣS (the engine stores ΣS in meta).
        sum_s = float(res.meta.get("sum_S", 0.0))
        extra = {"S vector": {a: v * sum_s for a, v in res.scores.items()}}
        extra_fmt = {"S vector": "{:.4f}"}
    elif method == "PROFILE_MATCHING":
        extra = {"Core factor score": ex.get("ncf_scores", {}), "Secondary factor score": ex.get("nsf_scores", {})}
        extra_fmt = {k: "{:.4f}" for k in extra}
    elif method == "COPELAND":
        extra = {"Wins": ex.get("wins", {}), "Ties": ex.get("ties", {}), "Losses": ex.get("losses", {})}
        extra_fmt = {k: "{:.0f}" for k in extra}
    _result_table(res, names, meta["score_label"], extra, extra_fmt)

    if method == "AHP":
        cr = float(indiv.consistency.get("CR", 0.0)) if indiv.consistency else 0.0
        if cr < 0.1:
            callout("ok", f"CR {cr:.4f}, below the 0.10 limit.", "Assessment is consistent")
        else:
            callout("warn", f"CR {cr:.4f}, above the 0.10 limit. Consider revising the pairwise comparisons.", "Assessment is not consistent enough")
        sugs = indiv.consistency.get("suggestions", []) if indiv.consistency else []
        if sugs:
            with st.expander("Suggestions to improve consistency"):
                st.dataframe(pd.DataFrame(sugs).astype(str), hide_index=True, width="stretch")

    winner = (top_alts(res.ranks) or [""])[0]
    show_chart(
        ranked_bar(pd.Series(res.scores), names, winner, meta["score_label"], f"{meta['label']} · {indiv.role}"),
        key=f"met_ind_bar_{method}_{dm_id}",
    )

    if method in ("SAW", "AHP"):
        fig = chart_stacked_contributions(result, dm_id, method, names, crit_names)
        if fig:
            show_chart(fig, key=f"met_contrib_{method}_{dm_id}")
    elif method == "TOPSIS":
        fig = chart_topsis_scatter(result, dm_id, names)
        if fig:
            show_chart(fig, key=f"met_topsis_{dm_id}")
    elif method == "COPELAND":
        fig = chart_copeland_matrix(result, names, dm_id=dm_id)
        if fig:
            show_chart(fig, key=f"met_cop_{dm_id}")
    elif method == "WP":
        with st.expander("Exponent of each criterion weight"):
            rows = [
                {
                    "Criterion": f"{c} · {crit_names.get(c, c)}",
                    "Direction": "Benefit" if crit_types.get(c) == "benefit" else "Cost",
                    "Weight": w,
                    "Exponent": w if crit_types.get(c) == "benefit" else -w,
                }
                for c, w in indiv.criteria_weights.items()
            ]
            st.dataframe(
                pd.DataFrame(rows).style.format({"Weight": "{:.4f}", "Exponent": "{:+.4f}"}),
                hide_index=True,
                width="stretch",
            )
    elif method == "PROFILE_MATCHING":
        core = ex.get("core_factors", [])
        sec = ex.get("secondary_factors", [])
        cw, sw = ex.get("cf_weight"), ex.get("sf_weight")
        cw_txt = f"{cw * 100:.0f}%" if isinstance(cw, (int, float)) else "60%"
        sw_txt = f"{sw * 100:.0f}%" if isinstance(sw, (int, float)) else "40%"
        render_html(
            '<div class="callout info"><div class="callout-body">',
            f"<b>Core factor ({cw_txt}):</b> {esc(', '.join(f'{crit_names.get(c, c)} ({c})' for c in core) or '-')}<br>",
            f"<b>Secondary factor ({sw_txt}):</b> {esc(', '.join(f'{crit_names.get(c, c)} ({c})' for c in sec) or '-')}",
            "</div></div>",
        )

    _steps(res, f"Calculation trace of {indiv.role}")


def _borda_view(result: RunResult, names: Dict[str, str]) -> None:
    bw = result.group.get("BORDA_WEIGHTED")
    bu = result.group.get("BORDA_UNWEIGHTED")
    col_w, col_u = st.columns(2, gap="large")
    for col, res, title, note, key in (
        (col_w, bw, "Weighted Borda", "Points are multiplied by each DM's vote weight.", "w"),
        (col_u, bu, "Unweighted Borda", "Every DM's vote counts the same.", "u"),
    ):
        with col:
            render_html(f'<div style="font-weight:600;font-size:1.05rem">{esc(title)}</div><div class="step-note">{esc(note)}</div>')
            if res is None:
                callout("warn", "Not present in the loaded run.")
                continue
            _winner_callout(res, names, title.lower(), "Points")
            _result_table(res, names, "Points")
            winner = (top_alts(res.ranks) or [""])[0]
            show_chart(ranked_bar(pd.Series(res.scores), names, winner, "Borda points", title), key=f"met_borda_{key}")

    fig = chart_stacked_borda_contributions(result, names)
    if fig:
        section("Who pushes each product")
        show_chart(fig, key="met_borda_contrib")
    if bw:
        _steps(bw, "Weighted Borda calculation trace")
    if bu:
        _steps(bu, "Unweighted Borda calculation trace")


# ── Page ──────────────────────────────────────────────────────────────────
def render(result: Optional[RunResult], session: Session) -> None:
    page_header(
        "Results by method",
        "Choose a method, then a point of view: the group consensus or a single decision maker.",
    )
    if result is None:
        need_run("metode", "the per-method comparison")
        return

    names = result.alternative_names
    method = st.radio(
        "Method",
        options=METHOD_ORDER,
        format_func=lambda m: METHODS[m]["label"],
        horizontal=True,
        label_visibility="collapsed",
        key="nav_method",
    )
    meta = METHODS[method]
    render_html(
        f'<div style="margin:1rem 0 0.2rem"><div class="eyebrow">{esc(meta["full"])}</div>',
        f'<div style="max-width:46rem;line-height:1.55;margin-top:0.2rem">{esc(meta["plain"])}</div></div>',
    )
    with st.expander("Formula"):
        st.latex(meta["formula"])

    if method == "BORDA":
        _borda_view(result, names)
        return

    dm_ids = list(result.individual.keys())
    perspective = st.radio(
        "Point of view",
        options=["Group"] + dm_ids,
        format_func=lambda p: "Group consensus" if p == "Group" else f"{p} · {result.individual[p].role}",
        horizontal=True,
        label_visibility="collapsed",
        key="pill_perspective",
    )
    st.write("")
    if perspective == "Group":
        _group_view(method, result, names)
    else:
        _individual_view(method, perspective, result, names, session)
