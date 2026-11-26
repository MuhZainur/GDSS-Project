"""Page 3: Team assessment. Each DM compares all criteria (AHP); the facilitator sets the DMs' vote weights."""
from typing import Dict, List, Optional, Tuple

import streamlit as st

from app import case_edit as ce
from app.components.charts import chart_criteria_weights
from app.components.pairwise_slider import render_pairwise_slider
from app.components.step_renderer import render_step
from app.theme import callout, chip, esc, page_header, render_html, section, show_chart
from engine.ahp import calculate_ahp_weights
from engine.schemas import DMInput, DMWeighting, Session


def _same_matrix(a, b) -> bool:
    """Compares two pairwise matrices numerically (2, 2.0 and '2' count as equal)."""
    try:
        return len(a) == len(b) and all(
            len(ra) == len(rb) and all(abs(ce.as_float(x) - ce.as_float(y)) < 1e-9 for x, y in zip(ra, rb))
            for ra, rb in zip(a, b)
        )
    except (ValueError, ZeroDivisionError, TypeError):
        return False


def _meter(cr: float) -> str:
    pos = max(0.0, min(cr / 0.2, 1.0)) * 100
    return (
        '<div class="meter"><div class="meter-track">'
        f'<div class="meter-pin" style="left:calc({pos:.1f}% - 2px)"></div></div>'
        '<div class="meter-scale"><span>0</span><span>limit 0.10</span><span>0,20+</span></div></div>'
    )


def _ahp(pairwise, labels: List[str], prefix: str):
    """(weights dict, CR, CI, lambda_max, steps, suggestions) or None when the matrix cannot be calculated."""
    try:
        w, l_max, ci, cr, steps, sugg = calculate_ahp_weights(pairwise_raw=pairwise, labels=labels, prefix_id=prefix)
    except Exception:
        return None
    return {k: float(x) for k, x in zip(labels, w)}, float(cr), float(ci), float(l_max), steps, sugg


def _saved_cr(session: Session, dm_id: str) -> Optional[float]:
    inp = session.dm_inputs.get(dm_id)
    if inp is None:
        return None
    res = _ahp(inp.pairwise, inp.criteria, f"dm.{dm_id}.crit")
    return res[1] if res else None


def current_vote_weights(session: Session) -> Dict[str, float]:
    """Vote weights under the current settings (without waiting for the analysis to run)."""
    dm_ids = [d.id for d in session.dms]
    w = session.dm_weighting
    if w.mode == "ahp" and w.pairwise:
        res = _ahp(w.pairwise, w.order or dm_ids, "dm.vote")
        if res:
            return res[0]
    return {d: 1.0 / len(dm_ids) for d in dm_ids}


def _consistency_panel(res, names: Dict[str, str], chart_title: str, chart_key: str) -> None:
    weights, cr, ci_v, l_max, _steps, sugg = res
    show_chart(chart_criteria_weights(weights, names, chart_title), key=chart_key)
    ok = cr < 0.1
    render_html(
        f'<div style="display:flex;align-items:center;gap:0.6rem;margin-top:0.2rem">'
        f'<b>Assessment consistency</b>{chip("Consistent" if ok else "Needs revision", "ok" if ok else "bad")}</div>',
        _meter(cr),
        f'<div class="step-note">CR {cr:.4f} · CI {ci_v:.4f} · λmax {l_max:.4f}</div>',
    )
    if not ok and sugg:
        items = "".join(
            f"<li><b>{esc(names.get(s['pair'][0], s['pair'][0]))}</b> vs <b>{esc(names.get(s['pair'][1], s['pair'][1]))}</b>: "
            f"now {esc(s['current'])}, suggested {esc(s['suggested'])}</li>"
            for s in sugg
        )
        render_html(
            '<div class="callout warn"><div class="callout-title">Suggested fixes</div>',
            f'<div class="callout-body"><ul style="margin:0;padding-left:1.1rem">{items}</ul></div></div>',
        )


def _pairwise_sliders(ids: List[str], labels: Dict[str, str], key_prefix: str, saved_pw, saved_order) -> List[List]:
    """Sliders for all pairs; the result is a full pairwise matrix (lower triangle = reciprocal)."""
    n = len(ids)
    pw: List[List] = [[1] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            a, b = ids[i], ids[j]
            val = render_pairwise_slider(
                label_a=labels.get(a, a),
                label_b=labels.get(b, b),
                key=f"{key_prefix}_{a}_{b}",
                current_val=ce.saved_pair(saved_pw, saved_order, a, b),
            )
            pw[i][j] = val
            pw[j][i] = ce.reciprocal(val)
    return pw


def render(session: Session) -> Session:
    page_header(
        "Team assessment",
        "Each decision maker compares all criteria to show which matter more to them. "
        "Changes here only affect the results after the analysis is run again.",
    )

    crit_ids = [c.id for c in session.criteria]
    crit_name = {c.id: c.name for c in session.criteria}
    dm_ids = [d.id for d in session.dms]
    dm_role = {d.id: d.role for d in session.dms}

    if len(crit_ids) < 2 or not dm_ids:
        callout("warn", "Add criteria and decision makers on the Case data page first.")
        return session

    # The overview is filled in at the end so it reflects the edits made in this run.
    overview_slot = st.container()

    # ── Editor for one DM ──────────────────────────────────────────────────────
    section("Edit the assessment", f"every person compares {len(crit_ids)} criteria ({len(crit_ids) * (len(crit_ids) - 1) // 2} pairs)")
    selected_dm = st.radio(
        "Decision maker",
        options=dm_ids,
        format_func=lambda d: dm_role.get(d, d),
        horizontal=True,
        label_visibility="collapsed",
        key="pill_dm_sel",
    )
    current = session.dm_inputs.get(selected_dm)

    left, right = st.columns([3, 2], gap="large")
    with left:
        render_html(
            '<div class="step-note">Slide towards the criterion you consider more important. '
            "The number shows how strongly (2 = slightly, 9 = absolutely). Every criterion must be assessed by everyone.</div>"
        )
        new_pairwise = _pairwise_sliders(
            crit_ids, crit_name, f"pw_{selected_dm}",
            current.pairwise if current else None, current.criteria if current else None,
        )

    res = _ahp(new_pairwise, crit_ids, f"dm.{selected_dm}.crit")
    with right:
        with st.container(key="live_panel"):
            render_html('<div class="eyebrow">Live result</div>')
            if res is None:
                callout("bad", "Weights cannot be calculated from this assessment.", "AHP calculation failed")
            else:
                _consistency_panel(res, crit_name, f"Criteria weights according to {dm_role.get(selected_dm, selected_dm)}", f"pen_w_{selected_dm}")

    if res is not None and (
        current is None
        or current.criteria != crit_ids
        or current.chosen_method != "AHP"
        or not _same_matrix(current.pairwise, new_pairwise)
    ):
        updated = dict(session.dm_inputs)
        updated[selected_dm] = DMInput(criteria=list(crit_ids), pairwise=new_pairwise, chosen_method="AHP")
        session = session.model_copy(update={"dm_inputs": updated})

    # ── Vote weights between DMs ────────────────────────────────────────────────
    section("Vote weights", "how much influence each person has when opinions are combined into the group decision")
    render_html(
        '<div class="explain"><b>Vote weights are not criteria weights.</b> '
        "Criteria weights show what matters <i>to one person</i> (filled in by each person above). "
        "Vote weights show <i>how much that person's vote counts</i> in the group decision, "
        "for example a managing director's vote can count more than a junior's. "
        "Choose equal when every vote is the same, or assess with AHP: compare who is more influential for this decision.</div>"
    )
    saved_mode = session.dm_weighting.mode if session.dm_weighting.mode in ("ahp", "equal") else "equal"
    mode_label = st.radio(
        "How to set the vote weights",
        options=["Equal", "Assessed with AHP"],
        index=0 if saved_mode == "equal" else 1,
        horizontal=True,
        key="pill_dmw_mode",
    )
    mode = "equal" if mode_label == "Equal" else "ahp"

    old_w = session.dm_weighting
    vote_left, vote_right = st.columns([3, 2], gap="large")
    vote_pairwise = old_w.pairwise
    vote_res = None
    with vote_left:
        if mode == "ahp":
            render_html('<div class="step-note">Slide towards the person whose vote should count for more.</div>')
            vote_pairwise = _pairwise_sliders(dm_ids, dm_role, "pw_dmw", old_w.pairwise, old_w.order or dm_ids)
            vote_res = _ahp(vote_pairwise, dm_ids, "dm.vote")
        else:
            render_html('<div class="step-note">Every decision maker gets the same vote weight.</div>')
    with vote_right:
        if mode == "ahp" and vote_res is not None:
            _consistency_panel(vote_res, dm_role, "Vote weights", "pen_dm_weights")
        elif mode == "ahp":
            callout("bad", "Vote weights cannot be calculated from this assessment.")
        else:
            eq = {d: 1.0 / len(dm_ids) for d in dm_ids}
            show_chart(chart_criteria_weights(eq, dm_role, "Vote weights"), key="pen_dm_weights")

    new_weighting = DMWeighting(mode=mode, pairwise=vote_pairwise, order=list(dm_ids))
    if mode == "ahp" and vote_res is None:
        new_weighting = old_w
    if (
        new_weighting.mode != old_w.mode
        or (old_w.order or []) != dm_ids
        or not _same_matrix(old_w.pairwise or [], new_weighting.pairwise or [])
    ):
        session = session.model_copy(update={"dm_weighting": new_weighting})

    if mode == "ahp" and vote_res is not None:
        with st.expander("How the vote weights are calculated"):
            for s in vote_res[4]:
                render_step(s)

    # ── Overview of all DMs (filled in last) ──────────────────────────────────
    with overview_slot:
        _overview(session)
    return session


def _overview(session: Session) -> None:
    section("Assessment status")
    votes = current_vote_weights(session)
    body = ""
    for dm in session.dms:
        cr = _saved_cr(session, dm.id)
        cr_cell = chip("Unreadable", "bad") if cr is None else chip(f"CR {cr:.3f}", "ok" if cr < 0.1 else "bad")
        who = f'<b>{esc(dm.role)}</b>' + (f' <span class="sub">{esc(dm.name)}</span>' if dm.name else "")
        body += (
            f'<tr><td>{who}<div class="sub">{esc(dm.id)}</div></td>'
            f"<td>{len(session.criteria)} criteria</td><td>{cr_cell}</td>"
            f'<td class="num">{votes.get(dm.id, 0.0) * 100:.1f}%</td></tr>'
        )
    render_html(
        '<table class="tbl"><thead><tr><th>Decision maker</th><th>Assessed</th><th>Consistency</th>',
        '<th class="num">Vote weight</th></tr></thead><tbody>',
        body,
        "</tbody></table>",
    )
    st.caption("A CR below 0.10 means the assessment is consistent. Vote weights follow the settings at the bottom of this page.")
