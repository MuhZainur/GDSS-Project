import pandas as pd
import streamlit as st

from app.theme import callout, esc, render_html
from engine.schemas import Step


def render_step(step: Step) -> None:
    """One calculation step: title, explanation, table, matrix/formula, then the result box."""
    render_html(f'<div class="step-title">{esc(step.title)}</div>')

    if step.explanation:
        st.markdown(step.explanation)

    if step.table:
        df = pd.DataFrame(step.table.rows, columns=step.table.columns)
        # Every cell becomes text so mixed tables (numbers, fractions, symbols) do not fail Arrow conversion.
        st.dataframe(df.astype(str), hide_index=True, width="stretch")

    if step.matrix and step.matrix.latex:
        st.latex(step.matrix.latex)

    if step.formula:
        st.latex(step.formula)

    if step.result:
        kind = {"ok": "ok", "bad": "bad", "warn": "warn"}.get(step.result.status or "info", "info")
        callout(kind, step.result.text)
