"""
Plotly charts. Visual rules:
- The winning/recommended choice uses ACCENT (terracotta); the other bars stay neutral.
- One alternative or criterion always uses the same category colour in every chart.
- One value axis per chart, labels directly on the bars, compact tooltips.
"""
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.insights import agreement_matrix, consensus, group_keys
from app.labels import GROUP_LABELS
from app.theme import ACCENT, BRAND, CAT, INK, LINE, MUTED, NEUTRAL_BAR, PAPER, SURFACE
from engine.schemas import RunResult

HIGHLIGHT_COLOR = ACCENT

def _natural(identifier: str):
    """Natural order of codes: C2 before C10."""
    digits = "".join(ch for ch in str(identifier) if ch.isdigit())
    return (int(digits) if digits else 0, str(identifier))


_CRIT_ORDER = [f"C{i}" for i in range(1, 13)]


def get_alt_color(alt_id: str) -> str:
    """A fixed colour per alternative based on the number in its code (A1 -> first colour, and so on)."""
    digits = "".join(ch for ch in str(alt_id) if ch.isdigit())
    idx = (int(digits) - 1) if digits else 0
    return CAT[idx % len(CAT)]


def get_crit_color(crit_id: str, ordered: Optional[List[str]] = None) -> str:
    order = ordered or _CRIT_ORDER
    idx = order.index(crit_id) if crit_id in order else len(order)
    return CAT[idx % len(CAT)]


def _fmt(v: float) -> str:
    return f"{v:.0f}" if float(v).is_integer() else f"{v:.4f}"


def _alt_label(a: str, names: Dict[str, str]) -> str:
    return f"{a} · {names.get(a, a)}"


def _wrap_label(text: str) -> str:
    """Splits a long label into two lines for the x axis."""
    if " " not in text:
        return text
    mid = len(text) // 2
    spaces = [i for i, ch in enumerate(text) if ch == " "]
    cut = min(spaces, key=lambda i: abs(i - mid))
    return text[:cut] + "<br>" + text[cut + 1:]


# ══ 1. Ranked bars ══════════════════════════════════════════════════════
def ranked_bar(series: pd.Series, names: Dict[str, str], winner: str, x_title: str, title: str) -> go.Figure:
    s = series.sort_values(ascending=True)
    colors = [ACCENT if a == winner else NEUTRAL_BAR for a in s.index]
    fig = go.Figure(
        go.Bar(
            x=s.values,
            y=[_alt_label(a, names) for a in s.index],
            orientation="h",
            marker_color=colors,
            text=[_fmt(v) for v in s.values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>" + x_title + ": %{x:.4f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=None,
        height=110 + 44 * len(s),
        margin=dict(l=10, r=60, t=56, b=40),
        showlegend=False,
    )
    return fig


chart_bar_scores = lambda scores, alt_names, title="Alternative Scores", highlight_winner=True: ranked_bar(
    pd.Series(scores),
    alt_names,
    max(scores, key=scores.get) if scores else "",
    "Score",
    title,
)


# ══ 2. Average rank ═══════════════════════════════════════════════════
def chart_average_rank(avg_rank: pd.Series, overall_best: str, alt_names: Dict[str, str]) -> go.Figure:
    """Dot chart: further left is better (1 = ranked first in every method)."""
    s = avg_rank.sort_values(ascending=True)
    n = max(len(s), 2)
    fig = go.Figure(
        go.Scatter(
            x=s.values,
            y=[_alt_label(a, alt_names) for a in s.index],
            mode="markers+text",
            text=[f"{v:.2f}" for v in s.values],
            textposition="middle right",
            textfont=dict(size=12),
            marker=dict(
                size=15,
                color=[ACCENT if a == overall_best else NEUTRAL_BAR for a in s.index],
                line=dict(color=INK, width=1),
            ),
            hovertemplate="%{y}<br>Average rank: %{x:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Average rank across all group methods",
        xaxis=dict(title="Average rank (left = better)", range=[0.7, n + 0.6], dtick=1),
        yaxis=dict(title=None, autorange="reversed"),
        height=110 + 44 * len(s),
        margin=dict(l=10, r=30, t=56, b=40),
        showlegend=False,
    )
    return fig


# ══ 3. Criteria profile radar ═════════════════════════════════════════════════
def chart_radar_criteria_profile(
    norm_matrix: pd.DataFrame,
    criteria_codes: List[str],
    alt_names: Dict[str, str],
    overall_best: str,
) -> go.Figure:
    fig = go.Figure()
    theta = criteria_codes + [criteria_codes[0]]
    for a in norm_matrix.index:
        r_vals = norm_matrix.loc[a, criteria_codes].tolist() + [norm_matrix.loc[a, criteria_codes[0]]]
        best = a == overall_best
        fig.add_trace(
            go.Scatterpolar(
                r=r_vals,
                theta=theta,
                fill="toself" if best else None,
                fillcolor="rgba(194,65,12,0.12)" if best else None,
                name=_alt_label(a, alt_names),
                line=dict(color=ACCENT if best else get_alt_color(a), width=3.2 if best else 1.4),
                opacity=1.0 if best else 0.55,
            )
        )
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 1], gridcolor="#E9E4D7", tickfont=dict(size=10, color=MUTED)),
            angularaxis=dict(gridcolor="#E9E4D7"),
        ),
        height=470,
        title="Criteria profile (values put on one scale, 1 = best)",
        margin=dict(l=40, r=40, t=60, b=30),
        legend=dict(orientation="h", y=-0.12),
    )
    return fig


# ══ 4. Criteria contribution (stacked) ══════════════════════════════════════════
def chart_stacked_contributions(
    result: RunResult,
    dm_id: str,
    model_name: str,
    alt_names: Dict[str, str],
    crit_names: Dict[str, str],
) -> Optional[go.Figure]:
    indiv = result.individual.get(dm_id)
    if not indiv:
        return None
    m_res = indiv.models.get(model_name)
    if not m_res or not m_res.contributions:
        return None

    contribs = m_res.contributions
    criteria = list(next(iter(contribs.values())).keys())
    alts = result.alternatives
    totals = {a: sum(contribs.get(a, {}).values()) for a in alts}
    order = [_alt_label(a, alt_names) for a in sorted(alts, key=lambda a: totals[a])]

    rows = [
        {
            "Alternative": _alt_label(a, alt_names),
            "Criterion": f"{c} · {crit_names.get(c, c)}",
            "Kontribusi": contribs.get(a, {}).get(c, 0.0),
            "_c": c,
        }
        for a in alts
        for c in criteria
    ]
    df = pd.DataFrame(rows)
    color_map = {f"{c} · {crit_names.get(c, c)}": get_crit_color(c) for c in criteria}
    fig = px.bar(
        df,
        x="Kontribusi",
        y="Alternative",
        color="Criterion",
        orientation="h",
        color_discrete_map=color_map,
        category_orders={"Alternative": order, "Criterion": list(color_map.keys())},
        title=f"Which criteria the score comes from ({model_name}, {dm_id})",
    )
    fig.update_traces(marker_line_color=SURFACE, marker_line_width=1)
    fig.update_layout(
        yaxis_title=None,
        height=130 + 44 * len(alts),
        margin=dict(l=10, r=20, t=56, b=40),
        legend=dict(orientation="h", y=-0.28, title=None),
    )
    return fig


def chart_stacked_borda_contributions(result: RunResult, alt_names: Dict[str, str]) -> Optional[go.Figure]:
    bw = result.group.get("BORDA_WEIGHTED")
    if not bw or not bw.contributions:
        return None

    contribs = bw.contributions
    dms = list(result.individual.keys())
    alts = result.alternatives
    totals = {a: sum(contribs.get(a, {}).values()) for a in alts}
    order = [_alt_label(a, alt_names) for a in sorted(alts, key=lambda a: totals[a])]

    rows = [
        {
            "Alternative": _alt_label(a, alt_names),
            "DM": f"{dm} · {result.individual[dm].role}",
            "Points": contribs.get(a, {}).get(dm, 0.0),
        }
        for a in alts
        for dm in dms
    ]
    df = pd.DataFrame(rows)
    color_map = {f"{dm} · {result.individual[dm].role}": CAT[i % len(CAT)] for i, dm in enumerate(dms)}
    fig = px.bar(
        df,
        x="Points",
        y="Alternative",
        color="DM",
        orientation="h",
        color_discrete_map=color_map,
        category_orders={"Alternative": order, "DM": list(color_map.keys())},
        title="Who pushes each alternative (weighted Borda points per DM)",
    )
    fig.update_traces(marker_line_color=SURFACE, marker_line_width=1)
    fig.update_layout(
        yaxis_title=None,
        height=130 + 44 * len(alts),
        margin=dict(l=10, r=20, t=56, b=40),
        legend=dict(orientation="h", y=-0.28, title=None),
    )
    return fig


# ══ 5. Heatmap & bump ════════════════════════════════════════════════════════
_RANK_SCALE = [[0.0, BRAND], [0.5, "#9DB9B6"], [1.0, "#EFEADD"]]


def _annotate_cells(fig: go.Figure, z, xs, ys, dark_max: float, fmt=lambda v: f"{v:g}") -> None:
    """Number in each cell: white on dark cells (z <= dark_max), ink on light cells."""
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            v = z[i][j]
            fig.add_annotation(
                x=x, y=y, text=fmt(v), showarrow=False,
                font=dict(size=13, color="#FFFFFF" if v <= dark_max else INK),
            )




def chart_group_rank_heatmap(result: RunResult, alt_names: Dict[str, str]) -> go.Figure:
    """Rank heatmap: alternatives x group models. Dark = good rank."""
    keys = group_keys(result)
    z = [[result.group[k].ranks.get(a, 0) for k in keys] for a in result.alternatives]
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[_wrap_label(GROUP_LABELS.get(k, k)) for k in keys],
            y=[_alt_label(a, alt_names) for a in result.alternatives],
            colorscale=_RANK_SCALE,
            zmin=1,
            zmax=len(result.alternatives),
            xgap=2,
            ygap=2,
            showscale=False,
            hovertemplate="%{y}<br>%{x}: rank %{z}<extra></extra>",
        )
    )
    xs = [_wrap_label(GROUP_LABELS.get(k, k)) for k in keys]
    ys = [_alt_label(a, alt_names) for a in result.alternatives]
    _annotate_cells(fig, z, xs, ys, dark_max=max(2, len(result.alternatives) // 3))
    fig.update_layout(
        title="Rank of each alternative in each group method",
        height=130 + 46 * len(result.alternatives),
        yaxis=dict(autorange="reversed"),
        xaxis=dict(side="top"),
        margin=dict(l=10, r=10, t=90, b=10),
    )
    return fig


def chart_rank_heatmap(result: RunResult, alt_names: Dict[str, str]) -> go.Figure:
    """Full heatmap: every method for each DM + every group method."""
    cols: List[str] = []
    all_ranks: Dict[str, List[int]] = {a: [] for a in result.alternatives}

    for dm_id, indiv in result.individual.items():
        for m_name, m_res in indiv.models.items():
            cols.append(f"{dm_id} {m_name}")
            for a in result.alternatives:
                all_ranks[a].append(m_res.ranks.get(a, 0))
    for g_name, g_res in result.group.items():
        cols.append(GROUP_LABELS.get(g_name, g_name))
        for a in result.alternatives:
            all_ranks[a].append(g_res.ranks.get(a, 0))

    z = [[all_ranks[a][j] for j in range(len(cols))] for a in result.alternatives]
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=cols,
            y=[_alt_label(a, alt_names) for a in result.alternatives],
            colorscale=_RANK_SCALE,
            zmin=1,
            zmax=len(result.alternatives),
            xgap=1,
            ygap=1,
            showscale=False,
            hovertemplate="%{y}<br>%{x}: rank %{z}<extra></extra>",
        )
    )
    ys = [_alt_label(a, alt_names) for a in result.alternatives]
    _annotate_cells(fig, z, cols, ys, dark_max=max(2, len(result.alternatives) // 3))
    fig.update_layout(
        title="Rank in every method, for each DM and the group",
        height=150 + 44 * len(result.alternatives),
        yaxis=dict(autorange="reversed"),
        xaxis=dict(tickangle=-60, side="top"),
        margin=dict(l=10, r=10, t=130, b=10),
    )
    return fig


def chart_bump(result: RunResult, alt_names: Dict[str, str]) -> go.Figure:
    keys = group_keys(result)
    n_alt = len(result.alternatives)
    best = consensus(result)["best"]
    labels = [_wrap_label(GROUP_LABELS.get(k, k)) for k in keys]
    fig = go.Figure()

    for a in result.alternatives:
        ys = [result.group[k].ranks.get(a, n_alt) for k in keys]
        is_best = a == best
        color = ACCENT if is_best else get_alt_color(a)
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=ys,
                mode="lines+markers+text" if is_best else "lines+markers",
                name=_alt_label(a, alt_names),
                text=[str(r) for r in ys] if is_best else None,
                textposition="top center",
                textfont=dict(color=ACCENT, size=12),
                line=dict(color=color, width=4 if is_best else 2),
                marker=dict(size=10 if is_best else 7, color=color),
                opacity=1.0 if is_best else 0.6,
                hovertemplate="%{fullData.name}<br>%{x}: rank %{y}<extra></extra>",
            )
        )
    fig.update_layout(
        title="Rank movement between group methods",
        yaxis=dict(autorange="reversed", title="Rank", dtick=1, range=[n_alt + 0.4, 0.6]),
        xaxis=dict(title=None),
        height=470,
        margin=dict(l=10, r=10, t=56, b=10),
        legend=dict(orientation="h", y=-0.22),
    )
    return fig


# ══ 6. TOPSIS & Copeland ═════════════════════════════════════════════════════
def chart_topsis_scatter(result: RunResult, dm_id: str, alt_names: Dict[str, str]) -> Optional[go.Figure]:
    indiv = result.individual.get(dm_id)
    if not indiv:
        return None
    topsis = indiv.models.get("TOPSIS")
    if not topsis or not topsis.extra:
        return None

    d_plus = topsis.extra.get("d_plus", {})
    d_minus = topsis.extra.get("d_minus", {})
    alts = result.alternatives
    winners = [a for a, r in topsis.ranks.items() if r == 1]
    w_id = winners[0] if winners else ""

    fig = go.Figure(
        go.Scatter(
            x=[d_plus.get(a, 0) for a in alts],
            y=[d_minus.get(a, 0) for a in alts],
            mode="markers+text",
            text=[_alt_label(a, alt_names) for a in alts],
            textposition="top center",
            marker=dict(size=13, color=[ACCENT if a == w_id else NEUTRAL_BAR for a in alts], line=dict(color=INK, width=1)),
            hovertemplate="%{text}<br>D+: %{x:.4f}<br>D−: %{y:.4f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Distance to the ideal and to the worst ({dm_id})",
        xaxis_title="Distance to the ideal (D+), smaller is better",
        yaxis_title="Distance to the worst (D−), larger is better",
        height=440,
        showlegend=False,
        margin=dict(l=10, r=20, t=56, b=40),
    )
    return fig


_DIVERGING = [[0.0, "#B8532F"], [0.5, "#F5F2EA"], [1.0, "#1F6F66"]]


def chart_copeland_matrix(
    result: RunResult,
    alt_names: Dict[str, str],
    model_key: str = "COPELAND_GROUP",
    dm_id: Optional[str] = None,
) -> Optional[go.Figure]:
    res = None
    if dm_id:
        indiv = result.individual.get(dm_id)
        if indiv:
            res = indiv.models.get("COPELAND")
    else:
        res = result.group.get(model_key)

    if not res or not res.extra or "match_matrix" not in res.extra:
        return None

    mm = res.extra["match_matrix"]
    alts = result.alternatives
    z_vals, text_vals = [], []
    for i, a in enumerate(alts):
        row_z, row_t = [], []
        for j, b in enumerate(alts):
            if i == j:
                row_z.append(0)
                row_t.append("–")
                continue
            if isinstance(mm, list):
                val = mm[i][j]
            elif isinstance(mm, dict):
                val = mm.get(a, {}).get(b, 0)
            else:
                val = 0
            row_z.append(val)
            row_t.append(f"{val:+.0f}" if float(val).is_integer() else f"{val:+.2f}")
        z_vals.append(row_z)
        text_vals.append(row_t)

    names = [_alt_label(a, alt_names) for a in alts]
    fig = go.Figure(
        go.Heatmap(
            z=z_vals,
            x=alts,
            y=alts,
            customdata=[[(names[i], names[j]) for j in range(len(alts))] for i in range(len(alts))],
            colorscale=_DIVERGING,
            zmid=0,
            text=text_vals,
            texttemplate="%{text}",
            xgap=2,
            ygap=2,
            showscale=False,
            hovertemplate="Row %{y} vs column %{x}: %{text}<extra></extra>",
        )
    )
    who = f"({dm_id})" if dm_id else "group"
    fig.update_layout(
        title=f"Who beats whom, Copeland {who} (green = row wins, red = row loses)",
        height=440,
        yaxis=dict(autorange="reversed", title="Alternative in the row"),
        xaxis=dict(side="top", title=None),
        margin=dict(l=10, r=10, t=100, b=10),
    )
    return fig


# ══ 7. Weights ═════════════════════════════════════════════════════════════════
def chart_criteria_weights(weights: Dict[str, float], crit_names: Dict[str, str], title: str = "Criteria weights") -> go.Figure:
    items = sorted(weights.items(), key=lambda kv: kv[1])
    fig = go.Figure(
        go.Bar(
            x=[w for _, w in items],
            y=[f"{c} · {crit_names.get(c, c)}" for c, _ in items],
            orientation="h",
            marker_color=[get_crit_color(c) for c, _ in items],
            text=[f"{w * 100:.1f}%" for _, w in items],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>Weight: %{x:.4f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        xaxis=dict(title=None, tickformat=".0%", range=[0, max([w for _, w in items] + [0.1]) * 1.25]),
        yaxis_title=None,
        height=100 + 44 * len(items),
        showlegend=False,
        margin=dict(l=10, r=50, t=50, b=20),
    )
    return fig


def chart_weights_bar(result: RunResult, alt_names: Dict[str, str], crit_names: Dict[str, str]) -> go.Figure:
    """Criteria weight composition of each DM (every bar adds up to 100%)."""
    dms = list(result.individual.keys())
    used = {c for dm in dms for c in result.individual[dm].criteria_weights}
    criteria = sorted(used, key=_natural)

    fig = go.Figure()
    for c in criteria:
        fig.add_trace(
            go.Bar(
                name=f"{c} · {crit_names.get(c, c)}",
                x=[f"{dm} · {result.individual[dm].role}" for dm in dms],
                y=[result.individual[dm].criteria_weights.get(c, 0.0) for dm in dms],
                marker_color=get_crit_color(c),
                marker_line_color=SURFACE,
                marker_line_width=1,
                hovertemplate="%{x}<br>" + c + ": %{y:.1%}<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="stack",
        title="What each DM emphasises (criteria weight composition)",
        yaxis=dict(title=None, tickformat=".0%"),
        height=420,
        margin=dict(l=10, r=10, t=56, b=40),
        legend=dict(orientation="h", y=-0.25, title=None),
    )
    return fig


def chart_dm_weights(result: RunResult) -> go.Figure:
    w = result.dm_weights.weights
    labels = [f"{dm} · {result.individual[dm].role}" if dm in result.individual else dm for dm in w]
    vals = list(w.values())
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=vals,
            marker_color=BRAND,
            text=[f"{v * 100:.1f}%" for v in vals],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}<br>Vote weight: %{y:.4f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Vote weight of each DM (consistency ratio CR = {result.dm_weights.CR:.4f})",
        yaxis=dict(title=None, tickformat=".0%", range=[0, max(vals + [0.1]) * 1.2]),
        height=360,
        showlegend=False,
        margin=dict(l=10, r=10, t=56, b=30),
    )
    return fig


def chart_agreement_heatmap(result: RunResult) -> go.Figure:
    keys, mat = agreement_matrix(result, "spearman")
    labels = [_wrap_label(GROUP_LABELS.get(k, k)) for k in keys]
    z = [[(v if v is not None else float("nan")) for v in row] for row in mat]
    text = [["" if v is None else f"{v:.2f}" for v in row] for row in mat]
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=labels,
            y=labels,
            colorscale=[[0.0, "#B8532F"], [0.5, "#F5F2EA"], [1.0, BRAND]],
            zmin=-1,
            zmax=1,
            text=text,
            texttemplate="%{text}",
            xgap=2,
            ygap=2,
            colorbar=dict(title="ρ", thickness=12),
            hovertemplate="%{y} and %{x}: ρ = %{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title="How similar the orderings of the methods are (Spearman correlation, 1 = identical)",
        height=470,
        yaxis=dict(autorange="reversed"),
        xaxis=dict(side="top"),
        margin=dict(l=10, r=10, t=110, b=10),
    )
    return fig
