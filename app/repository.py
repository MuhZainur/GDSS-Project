import os
import json
import csv
import io
from pathlib import Path
from typing import List, Dict, Any, Optional

from engine.schemas import Session, RunResult

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
SESSIONS_DIR = STORAGE_DIR / "sessions"
RUNS_DIR = STORAGE_DIR / "runs"
CHATS_DIR = STORAGE_DIR / "chats"

def init_storage():
    """Creates the storage directories if they do not exist."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    CHATS_DIR.mkdir(parents=True, exist_ok=True)

# ----------------- SESSION -----------------

def save_session(session: Session) -> Path:
    init_storage()
    sess_dir = SESSIONS_DIR / session.session_id
    sess_dir.mkdir(parents=True, exist_ok=True)
    file_path = sess_dir / "session.json"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(session.model_dump_json(indent=2))
    return file_path

def load_session(session_id: str) -> Optional[Session]:
    init_storage()
    file_path = SESSIONS_DIR / session_id / "session.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Session.model_validate(data)

def list_sessions() -> List[str]:
    init_storage()
    sessions = []
    if SESSIONS_DIR.exists():
        for p in SESSIONS_DIR.iterdir():
            if p.is_dir() and (p / "session.json").exists():
                sessions.append(p.name)
    return sorted(sessions)

# ----------------- RUNS -----------------

def export_rankings_csv(result: RunResult, include_wp: bool = True) -> str:
    """
    Long-format CSV:
    run_id,scope,dm_id,dm_role,model,is_chosen_method,alternative_id,alternative_name,score,rank
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "run_id", "scope", "dm_id", "dm_role", "model",
        "is_chosen_method", "alternative_id", "alternative_name", "score", "rank"
    ])

    run_id = result.run_id
    alt_names = result.alternative_names

    # 1. Individual models
    for dm_id, indiv in result.individual.items():
        role = indiv.role
        chosen = indiv.chosen_method.upper()

        for m_name, m_res in indiv.models.items():
            if m_name == "WP" and not include_wp:
                continue
            is_chosen = "true" if m_name.upper() == chosen else "false"
            for a_id in result.alternatives:
                score_val = m_res.scores.get(a_id, 0.0)
                rank_val = m_res.ranks.get(a_id, 0)
                writer.writerow([
                    run_id, "individual", dm_id, role, m_name,
                    is_chosen, a_id, alt_names.get(a_id, a_id),
                    f"{score_val:.6f}", rank_val
                ])

    # 2. Group models
    for g_name, g_res in result.group.items():
        for a_id in result.alternatives:
            score_val = g_res.scores.get(a_id, 0.0)
            rank_val = g_res.ranks.get(a_id, 0)
            writer.writerow([
                run_id, "group", "", "", g_name,
                "", a_id, alt_names.get(a_id, a_id),
                f"{score_val:.6f}", rank_val
            ])

    return output.getvalue()

def save_run(result: RunResult) -> Path:
    init_storage()
    run_dir = RUNS_DIR / result.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save results.json
    res_path = run_dir / "results.json"
    with open(res_path, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    # Save rankings.csv
    csv_content = export_rankings_csv(result, include_wp=True)
    with open(run_dir / "rankings.csv", "w", encoding="utf-8", newline="") as f:
        f.write(csv_content)

    return res_path

def load_run(run_id: str) -> Optional[RunResult]:
    init_storage()
    file_path = RUNS_DIR / run_id / "results.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return RunResult.model_validate(data)

def list_runs() -> List[str]:
    init_storage()
    runs = []
    if RUNS_DIR.exists():
        for p in RUNS_DIR.iterdir():
            if p.is_dir() and (p / "results.json").exists():
                runs.append(p.name)
    return sorted(runs, reverse=True)

# ----------------- CHATS -----------------

def save_chat(run_id: str, chat_id: str, chat_data: Dict[str, Any]) -> Path:
    init_storage()
    chat_dir = CHATS_DIR / run_id
    chat_dir.mkdir(parents=True, exist_ok=True)
    file_path = chat_dir / f"{chat_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, indent=2, ensure_ascii=False)
    return file_path

def load_chat(run_id: str, chat_id: str) -> Optional[Dict[str, Any]]:
    init_storage()
    file_path = CHATS_DIR / run_id / f"{chat_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_chats(run_id: str) -> List[str]:
    init_storage()
    chat_dir = CHATS_DIR / run_id
    if not chat_dir.exists():
        return []
    chats = []
    for p in chat_dir.glob("*.json"):
        chats.append(p.stem)
    return sorted(chats)

# ----------------- AI REPORTS -----------------

def _safe(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in str(name))


def save_analysis(run_id: str, engine_key: str, data: Dict[str, Any]) -> Path:
    """Stores a finished AI report per run and selected engine, so reopening the page never spends API quota again."""
    init_storage()
    d = RUNS_DIR / _safe(run_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"analysis_{_safe(engine_key)}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_analysis(run_id: str, engine_key: str) -> Optional[Dict[str, Any]]:
    init_storage()
    path = RUNS_DIR / _safe(run_id) / f"analysis_{_safe(engine_key)}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("success") else None
