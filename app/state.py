"""Streamlit session state: initialisation, widget reset, running the analysis, switching session/run."""
import json
import traceback
from pathlib import Path
from typing import Optional

import streamlit as st

from engine.pipeline import run_all
from engine.schemas import Session
from app import case_edit as ce
from app.insights import session_fingerprint
from app.repository import list_runs, load_run, save_run, save_session

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = ROOT / "data" / "sample_gpu_lengkap.json"

PAGES = ["Summary", "Case data", "Team assessment", "Results by method", "Compare", "AI assistant"]

# Every widget created by a page uses one of these prefixes, so they can all be cleared at once.
WIDGET_PREFIXES = ("dm_", "pw_", "sess_", "wi_", "mt_", "pill_", "ed_")


def load_sample_session() -> Session:
    with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
        return ce.sync_session(Session.model_validate(json.load(f)))


def init_state() -> None:
    if "session" not in st.session_state:
        st.session_state.session = load_sample_session()
    st.session_state.setdefault("run_result", None)
    st.session_state.setdefault("run_fp", None)          # fingerprint of the data when the analysis was run
    st.session_state.setdefault("run_source", None)      # "new" | "history"
    st.session_state.setdefault("run_history", list_runs())
    st.session_state.setdefault("nav_page", PAGES[0])
    st.session_state.setdefault("flash", None)
    st.session_state.setdefault("uploader_n", 0)


def clear_widget_state() -> None:
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(WIDGET_PREFIXES):
            del st.session_state[k]


def set_flash(kind: str, text: str, detail: Optional[str] = None) -> None:
    st.session_state.flash = {"kind": kind, "text": text, "detail": detail}


def go_to(page: str) -> None:
    """Used as on_click: switch page before the rerun; safe for the widget named nav_page."""
    st.session_state.nav_page = page


def replace_session(new_session: Session, message: str) -> None:
    # Every incoming session (sample, saved, uploaded, empty) is aligned: each DM assesses all criteria.
    adjusted = any(
        set(i.criteria) != {c.id for c in new_session.criteria} or i.chosen_method != "AHP"
        for i in new_session.dm_inputs.values()
    ) or set(new_session.dm_inputs) != {d.id for d in new_session.dms}
    new_session = ce.sync_session(new_session)
    if adjusted:
        message += " Each decision maker's assessment was adjusted to cover all criteria (pairs never assessed before are set to 'equally important')."
    st.session_state.session = new_session
    st.session_state.run_result = None
    st.session_state.run_fp = None
    st.session_state.run_source = None
    clear_widget_state()
    set_flash("ok", message)


def reset_to_sample() -> None:
    replace_session(load_sample_session(), "Sample data reloaded.")


def new_blank_case() -> None:
    replace_session(ce.blank_session(), "Empty case created. Start on the Case data page.")
    st.session_state.nav_page = "Case data"


def load_saved_session(session_id: str) -> None:
    from app.repository import load_session

    try:
        loaded = load_session(session_id)
    except Exception as exc:  # corrupt file / old schema
        set_flash("bad", f"Session '{session_id}' could not be read.", str(exc))
        return
    if loaded is None:
        set_flash("bad", f"Session '{session_id}' was not found.")
        return
    replace_session(loaded, f"Session '{session_id}' loaded.")


def save_current_session() -> None:
    try:
        save_session(st.session_state.session)
        set_flash("ok", f"Session '{st.session_state.session.session_id}' saved on the server.")
    except OSError as exc:
        set_flash("warn", "Saving on the server failed. Use the JSON download button.", str(exc))


def run_analysis() -> None:
    """Runs every model on the active session. Called as on_click."""
    session: Session = st.session_state.session
    problems = ce.blocking_problems(session)
    if problems:
        extra = f" (and {len(problems) - 3} more)" if len(problems) > 3 else ""
        set_flash("bad", "The data cannot be analysed yet: " + " ".join(problems[:3]) + extra)
        st.session_state.nav_page = "Case data"
        return
    try:
        result = run_all(session)
    except Exception as exc:
        set_flash("bad", "The calculation failed. Check the case data and the team assessment.", traceback.format_exc())
        return
    st.session_state.run_result = result
    st.session_state.run_fp = session_fingerprint(session)
    st.session_state.run_source = "new"
    st.session_state.nav_page = PAGES[0]
    try:
        save_run(result)
        st.session_state.run_history = list_runs()
        set_flash("ok", f"Analysis finished. Run ID: {result.run_id}")
    except OSError as exc:
        set_flash("warn", "Analysis finished, but the history could not be saved on the server.", str(exc))


def load_history_run(run_id: str) -> None:
    try:
        loaded = load_run(run_id)
    except Exception as exc:
        set_flash("bad", f"Run '{run_id}' could not be read (format mismatch).", str(exc))
        return
    if loaded is None:
        set_flash("bad", f"Run '{run_id}' was not found.")
        return
    st.session_state.run_result = loaded
    st.session_state.run_fp = None
    st.session_state.run_source = "history"
    st.session_state.nav_page = PAGES[0]
    set_flash("info", f"Run '{run_id}' loaded from history.")


def run_status() -> tuple:
    """(kind, text) for the status chip in the masthead."""
    result = st.session_state.run_result
    if result is None:
        return "warn", "Not analysed yet"
    if st.session_state.run_source == "history":
        return "info", f"History run {result.run_id}"
    if st.session_state.run_fp == session_fingerprint(st.session_state.session):
        return "ok", "Analysis up to date"
    return "warn", "Data changed, run again"
