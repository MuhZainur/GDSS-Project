import json
from pathlib import Path
import pytest

from engine.schemas import Session
from engine.pipeline import run_all
from app.repository import (
    save_session,
    load_session,
    list_sessions,
    save_run,
    load_run,
    list_runs,
    export_rankings_csv
)

def test_repository_save_load_session():
    data_path = Path(__file__).resolve().parent.parent / "data" / "sample_case.json"
    with open(data_path, "r", encoding="utf-8") as f:
        session = Session.model_validate(json.load(f))

    save_path = save_session(session)
    assert save_path.exists()

    loaded = load_session(session.session_id)
    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert len(loaded.alternatives) == 7

    sessions = list_sessions()
    assert session.session_id in sessions

def test_repository_save_load_run_and_csv():
    data_path = Path(__file__).resolve().parent.parent / "data" / "sample_case.json"
    with open(data_path, "r", encoding="utf-8") as f:
        session = Session.model_validate(json.load(f))

    result = run_all(session, run_id="test-run-123")
    save_path = save_run(result)
    assert save_path.exists()

    loaded_run = load_run("test-run-123")
    assert loaded_run is not None
    assert loaded_run.run_id == "test-run-123"

    # Standard CSV length (without WP) -> 231 data lines (+ 1 header line = 232 lines)
    csv_str_no_wp = export_rankings_csv(result, include_wp=False)
    lines_no_wp = [line for line in csv_str_no_wp.strip().split("\n") if line.strip()]
    header = lines_no_wp[0]
    data_lines_no_wp = lines_no_wp[1:]
    assert len(data_lines_no_wp) == 231, f"There must be 231 data lines, got {len(data_lines_no_wp)}"

    # Full CSV length (with WP) -> 231 + 35 = 266 data lines
    csv_str_with_wp = export_rankings_csv(result, include_wp=True)
    lines_with_wp = [line for line in csv_str_with_wp.strip().split("\n") if line.strip()]
    data_lines_with_wp = lines_with_wp[1:]
    assert len(data_lines_with_wp) == 266
