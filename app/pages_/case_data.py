"""Page 2: Case data. Everything in the case (products, criteria, values, decision makers) can be edited here."""
from typing import Dict, List

import pandas as pd
import streamlit as st

from app import case_edit as ce
from app.theme import callout, chip, esc, page_header, render_html, section, stat_row
from engine.schemas import Alternative, Criterion, DM, Session

TYPE_LABEL = {"benefit": "Benefit", "cost": "Cost"}
TYPE_OPTIONS = ["Benefit", "Cost"]
TYPE_HELP = "Benefit: higher is better (for example performance, margin). Cost: lower is better (for example cost, risk, time)."


# ── Button callbacks (called before the rerun, so changing session_state is safe) ──
def _mutate(fn, *args) -> None:
    st.session_state.session = fn(st.session_state.session, *args)


def _num(v: float) -> str:
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def _shade(session: Session):
    """Per-column shading: darker = better for that criterion (benefit/cost direction already taken into account)."""
    cmap = {c.id: c for c in session.criteria}

    def apply(col: pd.Series):
        crit = cmap.get(col.name)
        if crit is None:
            return [""] * len(col)
        lo, hi = float(col.min()), float(col.max())
        out = []
        for v in col:
            if hi == lo:
                g = 0.5
            elif crit.type.lower() == "benefit":
                g = (v - lo) / (hi - lo)
            else:
                g = (hi - v) / (hi - lo)
            out.append(f"background-color: rgba(14,59,63,{0.05 + 0.40 * g:.2f})")
        return out

    return apply


def _header(*cols: str, widths: List[float]) -> None:
    cells = st.columns(widths, vertical_alignment="center")
    for cell, text in zip(cells, cols):
        cell.markdown(f'<div class="col-head">{esc(text)}</div>', unsafe_allow_html=True)


# ── Page sections ────────────────────────────────────────────────────
def _problems(session: Session) -> None:
    issues = ce.validate_case(session)
    bad = [t for k, t in issues if k == "bad"]
    warn = [t for k, t in issues if k == "warn"]
    if bad:
        items = "".join(f"<li>{esc(t)}</li>" for t in bad)
        render_html(
            '<div class="callout bad"><div class="callout-title">The data cannot be analysed yet</div>',
            f'<div class="callout-body"><ul style="margin:0;padding-left:1.1rem">{items}</ul></div></div>',
        )
    if warn:
        items = "".join(f"<li>{esc(t)}</li>" for t in warn)
        render_html(
            '<div class="callout warn"><div class="callout-title">Needs a check</div>',
            f'<div class="callout-body"><ul style="margin:0;padding-left:1.1rem">{items}</ul></div></div>',
        )


def _about(session: Session) -> Session:
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("Case title", value=session.title, key="ed_title")
        goal = st.text_area("Decision goal", value=session.goal, key="ed_goal", height=90)
    with c2:
        company = st.text_input("Organisation name (optional)", value=session.company or "", key="ed_company")
        st.caption(f"Session ID: `{session.session_id}`")
    if (title, goal, company) != (session.title, session.goal, session.company or ""):
        session = session.model_copy(update={"title": title, "goal": goal, "company": company})
    return session


def _alternatives(session: Session) -> Session:
    section("Candidate products", f"{len(session.alternatives)} of at most {ce.MAX_ALTERNATIVES}; at least {ce.MIN_ALTERNATIVES}")
    widths = [0.8, 3, 2.2, 3.4, 0.9]
    _header("Code", "Product name", "Segment", "Description", "", widths=widths)
    edited: List[Alternative] = []
    can_delete = len(session.alternatives) > ce.MIN_ALTERNATIVES
    for a in session.alternatives:
        c_id, c_name, c_seg, c_desc, c_del = st.columns(widths, vertical_alignment="center")
        c_id.markdown(chip(a.id), unsafe_allow_html=True)
        name = c_name.text_input("Product name", value=a.name, key=f"ed_alt_name_{a.id}", label_visibility="collapsed")
        seg = c_seg.text_input("Segment", value=a.segment or "", key=f"ed_alt_seg_{a.id}", label_visibility="collapsed")
        desc = c_desc.text_input("Description", value=a.desc or "", key=f"ed_alt_desc_{a.id}", label_visibility="collapsed")
        c_del.button(
            "Remove", key=f"ed_alt_del_{a.id}", on_click=_mutate, args=(ce.remove_alternative, a.id),
            disabled=not can_delete, help="Remove this product from the case" if can_delete else f"At least {ce.MIN_ALTERNATIVES} products",
        )
        edited.append(a.model_copy(update={"name": name, "segment": seg or None, "desc": desc or None}))
    st.button(
        "Add product", key="ed_alt_add", on_click=_mutate, args=(ce.add_alternative,),
        disabled=len(session.alternatives) >= ce.MAX_ALTERNATIVES,
    )
    if edited != session.alternatives:
        session = session.model_copy(update={"alternatives": edited})
    return session


def _criteria(session: Session) -> Session:
    section("Assessment criteria", f"{len(session.criteria)} of at most {ce.MAX_CRITERIA}; at least {ce.MIN_CRITERIA}")
    widths = [0.8, 3, 2.2, 1.7, 0.9]
    _header("Code", "Criterion name", "Unit", "Benefit / Cost", "", widths=widths)
    edited: List[Criterion] = []
    can_delete = len(session.criteria) > ce.MIN_CRITERIA
    for c in session.criteria:
        c_id, c_name, c_unit, c_type, c_del = st.columns(widths, vertical_alignment="center")
        c_id.markdown(chip(c.id), unsafe_allow_html=True)
        name = c_name.text_input("Criterion name", value=c.name, key=f"ed_crit_name_{c.id}", label_visibility="collapsed")
        unit = c_unit.text_input("Unit", value=c.unit or "", key=f"ed_crit_unit_{c.id}", label_visibility="collapsed")
        current = TYPE_LABEL.get(c.type.lower(), "Benefit")
        typ = c_type.selectbox(
            "Benefit or Cost", TYPE_OPTIONS, index=TYPE_OPTIONS.index(current),
            key=f"ed_crit_type_{c.id}", label_visibility="collapsed", help=TYPE_HELP,
        )
        c_del.button(
            "Remove", key=f"ed_crit_del_{c.id}", on_click=_mutate, args=(ce.remove_criterion, c.id),
            disabled=not can_delete, help="Remove this criterion; the team assessment is adjusted too" if can_delete else f"At least {ce.MIN_CRITERIA} criteria",
        )
        edited.append(c.model_copy(update={"name": name, "unit": unit or None, "type": typ.lower()}))
    st.button(
        "Add criterion", key="ed_crit_add", on_click=_mutate, args=(ce.add_criterion,),
        disabled=len(session.criteria) >= ce.MAX_CRITERIA,
    )
    st.caption("Benefit: higher is better. Cost: lower is better. Each decision maker fills in the criteria comparisons on the Team assessment page.")
    if edited != session.criteria:
        session = session.model_copy(update={"criteria": edited})
    return session


def _values(session: Session) -> Session:
    section("Value of each product", "click a cell to change a number; data from Excel can be pasted directly")
    crit_ids = [c.id for c in session.criteria]
    alt_ids = [a.id for a in session.alternatives]

    # The table shape decides the editor's identity: changing products/criteria creates a new editor.
    sig = "_".join(alt_ids) + "__" + "_".join(crit_ids)
    widget_key, base_key = f"ed_vals_{sig}", f"ed_valsbase_{sig}"

    def _frame() -> pd.DataFrame:
        df = pd.DataFrame(
            {c: [float(session.values.get(a, {}).get(c, 0.0)) for a in alt_ids] for c in crit_ids},
            index=[f"{a.id} · {a.name}" for a in session.alternatives],
        )
        df.index.name = "Product"
        return df

    # The editor always gets the same base table while it is open, so edits do not create a new editor
    # and are not overwritten. The base table is rebuilt every time this page is opened.
    if widget_key not in st.session_state or base_key not in st.session_state:
        st.session_state[base_key] = _frame()
    base: pd.DataFrame = st.session_state[base_key]

    config: Dict[str, object] = {
        c.id: st.column_config.NumberColumn(
            f"{c.name}" + (f" ({c.unit})" if c.unit else ""),
            help=f"{TYPE_LABEL.get(c.type.lower(), 'Benefit')}: " + ("higher is better" if c.type.lower() == "benefit" else "lower is better"),
            format="%g",
            step=None,
            required=True,
        )
        for c in session.criteria
    }
    edited = st.data_editor(
        base, column_config=config, num_rows="fixed", width="stretch", key=widget_key,
        height=min(35 * (len(base) + 1) + 3, 460),
    )
    table = {
        aid: {cid: edited.iloc[i][cid] for cid in crit_ids}
        for i, aid in enumerate(alt_ids)
    }
    session = ce.apply_value_table(session, table)

    with st.expander("Show colour map (darker = better)"):
        st.dataframe(
            _frame().style.apply(_shade(session), axis=0).format(_num),
            column_config={c.id: st.column_config.Column(c.name) for c in session.criteria},
            width="stretch",
        )
    return session


def _dms(session: Session) -> Session:
    section("Decision makers", f"{len(session.dms)} of at most {ce.MAX_DMS}; at least {ce.MIN_DMS}")
    widths = [0.8, 3.2, 3.4, 0.9]
    _header("Code", "Title / role", "Name (optional)", "", widths=widths)
    edited: List[DM] = []
    can_delete = len(session.dms) > ce.MIN_DMS
    for d in session.dms:
        c_id, c_role, c_name, c_del = st.columns(widths, vertical_alignment="center")
        c_id.markdown(chip(d.id), unsafe_allow_html=True)
        role = c_role.text_input("Title or role", value=d.role, key=f"ed_dm_role_{d.id}", label_visibility="collapsed")
        name = c_name.text_input("Name", value=d.name or "", key=f"ed_dm_name_{d.id}", label_visibility="collapsed")
        c_del.button(
            "Remove", key=f"ed_dm_del_{d.id}", on_click=_mutate, args=(ce.remove_dm, d.id),
            disabled=not can_delete, help="Remove this decision maker" if can_delete else f"At least {ce.MIN_DMS} people",
        )
        edited.append(d.model_copy(update={"role": role, "name": name or None}))
    st.button("Add decision maker", key="ed_dm_add", on_click=_mutate, args=(ce.add_dm,), disabled=len(session.dms) >= ce.MAX_DMS)
    st.caption("Titles are free text (for example Product Manager, Branch Head, Team Lead). Each person's assessment and vote weight are set on the Team assessment page.")
    if edited != session.dms:
        session = session.model_copy(update={"dms": edited})
    return session


def render(session: Session) -> Session:
    page_header(
        "Case data",
        "Fill in your case: the products being compared, the assessment criteria, the value of each product, and who the decision makers are.",
    )

    summary_slot = st.container()  # filled at the end so it reflects the edits made in this run

    section("About the case")
    session = _about(session)
    session = _alternatives(session)
    session = _criteria(session)
    session = _values(session)
    session = _dms(session)

    with summary_slot:
        bad = any(k == "bad" for k, _ in ce.validate_case(session))
        stat_row(
            [
                ("Candidate products", str(len(session.alternatives)), "alternatives"),
                ("Criteria", str(len(session.criteria)), "assessed by every decision maker"),
                ("Decision makers", str(len(session.dms)), ", ".join(d.role for d in session.dms[:3]) + ("…" if len(session.dms) > 3 else "")),
                ("Data status", "Not ready" if bad else "Ready", "see the notes below" if bad else "can be analysed"),
            ]
        )
        _problems(session)
    return session
