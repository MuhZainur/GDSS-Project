"""
Decision Room: the GDSS (Group Decision Support System) interface for business teams.
Run with: streamlit run app/main.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import streamlit as st

st.set_page_config(
    page_title="Decision Room",
    page_icon=":material/balance:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from app import state
from app.pages_ import assessment, assistant, case_data, compare, methods, summary
from app.repository import list_sessions
from app.theme import callout, chip, esc, inject_css, render_html
from engine.schemas import Session

inject_css()
state.init_state()


# ── Sidebar: advanced settings ─────────────────────────────────────────────
def sidebar() -> None:
    with st.sidebar:
        st.markdown("### Session and data")
        st.button("Reload sample data", on_click=state.reset_to_sample, key="side_reset", width="stretch")
        st.button("Start an empty case", on_click=state.new_blank_case, key="side_new", width="stretch",
                  help="Clears every field so you can start your own case")

        saved = list_sessions()
        if saved:
            pick = st.selectbox("Sessions saved on the server", saved, key="side_sess_pick")
            st.button("Load this session", on_click=state.load_saved_session, args=(pick,), key="side_sess_load", width="stretch")
        st.button("Save session on the server", on_click=state.save_current_session, key="side_sess_save", width="stretch")

        st.download_button(
            "Download session (JSON)",
            data=st.session_state.session.model_dump_json(indent=2),
            file_name=f"session_{st.session_state.session.session_id}.json",
            mime="application/json",
            key="side_sess_dl",
            width="stretch",
        )
        up = st.file_uploader("Load a session from a JSON file", type=["json"], key=f"side_upload_{st.session_state.uploader_n}")
        if up is not None:
            try:
                new_session = Session.model_validate(json.load(up))
            except Exception as exc:
                st.error(f"The file could not be read as a session: {exc}")
            else:
                state.replace_session(new_session, f"Session from file '{up.name}' loaded.")
                st.session_state.uploader_n += 1  # clear the uploader so it is not processed again and again
                st.rerun()

        st.markdown("### Analysis history")
        hist = st.session_state.run_history
        if hist:
            run_pick = st.selectbox("Saved runs", hist, key="side_run_pick")
            st.button("Load this run", on_click=state.load_history_run, args=(run_pick,), key="side_run_load", width="stretch")
        else:
            st.caption("No saved runs yet.")

        st.markdown("### AI API keys")
        st.caption("Kept only in this browser session. For a deployment, set them through .env or the server secrets.")
        g = st.text_input("Google Gemini", value=st.session_state.get("custom_gemini_key", ""), type="password", key="side_key_gemini")
        if g.strip():
            st.session_state.custom_gemini_key = g.strip()
        o = st.text_input("OpenRouter", value=st.session_state.get("custom_api_key", ""), type="password", key="side_key_openrouter")
        if o.strip():
            st.session_state.custom_api_key = o.strip()


# ── Masthead ─────────────────────────────────────────────────────────────────
def masthead() -> None:
    session: Session = st.session_state.session
    col_brand, col_status, col_run = st.columns([5, 3.2, 1.6], vertical_alignment="center")
    with col_brand:
        sub = " · ".join(x for x in [session.company, session.title] if x)
        render_html(
            '<div class="masthead"><div class="mark"></div><div>',
            '<div class="brand-name">Decision Room</div>',
            f'<div class="brand-sub">{esc(sub)}</div></div></div>',
        )
    kind, text = state.run_status()
    with col_status:
        render_html(f'<div class="status-line">{chip(text, kind)}</div>')
    with col_run:
        label = "Run analysis" if st.session_state.run_result is None else "Recalculate"
        st.button(label, type="primary", on_click=state.run_analysis, key="mast_run", width="stretch")


def flash() -> None:
    msg = st.session_state.get("flash")
    if not msg:
        return
    st.session_state.flash = None
    callout(msg["kind"], msg["text"])
    if msg.get("detail"):
        with st.expander("Technical details"):
            st.code(msg["detail"])


sidebar()
masthead()

st.radio("Page", state.PAGES, horizontal=True, label_visibility="collapsed", key="nav_page")
flash()

session: Session = st.session_state.session
result = st.session_state.run_result
page = st.session_state.nav_page

# Warning about stale results on the pages that show results
if result is not None and page in ("Summary", "Results by method", "Compare", "AI assistant"):
    kind, _ = state.run_status()
    if kind == "warn":
        callout("warn", "The case data or the team assessment changed after this analysis was run. Press Recalculate so the numbers below follow.", "Results not updated")

if page == "Summary":
    summary.render(result, session)
elif page == "Case data":
    st.session_state.session = case_data.render(session)
elif page == "Team assessment":
    st.session_state.session = assessment.render(session)
elif page == "Results by method":
    methods.render(result, session)
elif page == "Compare":
    compare.render(result, session)
else:
    assistant.render(result, session)

render_html('<div class="step-note" style="margin-top:3rem;border-top:1px solid var(--line);padding-top:0.8rem">'
            + (f"{esc(session.data_note)} " if session.data_note else "")
            + "Numbers are shown to 4 decimals while the calculation uses full precision; "
            "a difference of about 0.001 when checking by hand is normal.</div>")
