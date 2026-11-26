"""Interface pieces shared by several pages."""
import streamlit as st

from app.state import go_to, run_analysis
from app.theme import callout


def need_run(page_key: str, what: str = "this page") -> None:
    """Empty state for pages that need analysis results."""
    callout("info", f"The content of {what} appears once the analysis has run. The sample data is ready, so there is nothing to fill in first.", "No results yet")
    c1, c2, _ = st.columns([1.3, 1.3, 4])
    c1.button("Run analysis", type="primary", on_click=run_analysis, key=f"need_run_{page_key}", width="stretch")
    c2.button("View case data", on_click=go_to, args=("Case data",), key=f"need_data_{page_key}", width="stretch")
