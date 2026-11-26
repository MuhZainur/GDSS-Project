"""Page 6: AI assistant (analysis report and chat)."""
import os
import uuid
from typing import Dict, List, Optional

import streamlit as st

from app.insights import consensus, dm_picks
from app.labels import group_label
from app.pages_.common import need_run
from app.repository import list_chats, load_analysis, load_chat, save_analysis
from app.theme import callout, chip, esc, page_header, render_html
from engine.schemas import RunResult, Session
from llm.analyze import run_analysis
from llm.chat import chat_step
from llm.payload import build_llm_payload

# Gemini 4 Hydrogen (thinking low) plus the free OpenRouter models above 29B parameters (see llm/client.py).
AI_MODELS = {
    "Gemini 4 Hydrogen (thinking low, recommended)": ("gemini", "gemini-4-hydrogen"),
    "OpenRouter · Nemotron 3 Ultra 550B (free)": ("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free"),
    "OpenRouter · Dots3-Note 280B (free)": ("openrouter", "dots-studio/dots-3-note-preview:free"),
    "OpenRouter · Nemotron 3.5 Super VL 120B (free)": ("openrouter", "nvidia/nemotron-3.5-super-vl:free"),
    "OpenRouter · ERNIE 5.5 Flash 280B (free)": ("openrouter", "baidu/ernie-5.5-flash-preview:free"),
    "OpenRouter · automatic (first free model that answers)": ("openrouter", None),
}


def stored_key(provider: str) -> str:
    """API key of this browser session, or from the server environment. Never written to os.environ."""
    if provider == "gemini":
        return (st.session_state.get("custom_gemini_key") or os.getenv("GOOGLE_API_KEY", "")).strip()
    return (st.session_state.get("custom_api_key") or os.getenv("OPENROUTER_API_KEY", "")).strip()


def all_keys() -> Dict[str, str]:
    """Keys of both providers, so a failed engine can fall back to the other provider."""
    return {"gemini": stored_key("gemini"), "openrouter": stored_key("openrouter")}


def _starter_questions(result: RunResult, session: Session) -> List[str]:
    names = result.alternative_names
    crit_names = {c.id: c.name for c in session.criteria}
    cons = consensus(result)
    best = names.get(cons["best"], cons["best"])
    qs = []
    if cons["differ"]:
        k = cons["differ"][0]
        other = [a for a, r in result.group[k].ranks.items() if r == 1]
        other_name = names.get(other[0], other[0]) if other else "another product"
        qs.append(f"Why does {group_label(k)} pick {other_name}, while most methods pick {best}?")
    else:
        qs.append(f"Why do all methods agree on {best}?")
    qs.append(f"What are the risks of choosing {best}?")
    qs.append("Which method is the most reliable for this case, and why?")
    qs.append(f"Which market factors or recent trends are relevant to the case \"{session.title}\"?")
    picks = dm_picks(result, crit_names)
    if picks:
        top = max(picks, key=lambda p: p["vote_weight"])
        qs.append(f"What would happen if {top['role']}'s vote weight were reduced to match the other DMs?")
    return qs


def _sources(sources) -> None:
    if sources:
        with st.expander(f"References ({len(sources)})"):
            for idx, s in enumerate(sources, 1):
                st.markdown(f"**[{idx}] [{s['title']}]({s['url']})**\n\n{s['snippet']}")


def render(result: Optional[RunResult], session: Session) -> None:
    page_header(
        "AI assistant",
        "The AI reads the calculation results and explains them. It does not recalculate: every number must come from the analysis results.",
    )
    if result is None:
        need_run("ai", "the AI assistant")
        return

    col_model, col_stat = st.columns([2.2, 1], vertical_alignment="bottom")
    with col_model:
        sel_label = st.selectbox("AI engine", options=list(AI_MODELS.keys()), key="ai_model")
    provider, model_name = AI_MODELS[sel_label]
    active_key = stored_key(provider)
    with col_stat:
        provider_name = "Google Gemini" if provider == "gemini" else "OpenRouter"
        render_html(chip(f"{provider_name} ready", "ok") if active_key else chip(f"{provider_name} key missing", "warn"))

    if not active_key:
        inp = st.text_input(
            f"{provider_name} API key",
            type="password",
            key=f"ai_key_input_{provider}",
            help="Kept only for this browser session and never written to the server.",
        )
        if inp.strip():
            st.session_state["custom_gemini_key" if provider == "gemini" else "custom_api_key"] = inp.strip()
            st.rerun()
        callout("info", "Enter an API key to enable the report and the chat. A key can also be set in the .env file or in the secrets of a deployment.")
        return

    mode = st.radio(
        "Mode",
        ["Analysis report", "Ask the assistant"],
        horizontal=True,
        label_visibility="collapsed",
        key="pill_ai_mode",
    )
    st.write("")
    if mode == "Analysis report":
        _report(result, session, active_key, provider, model_name, sel_label)
    else:
        _chat(result, session, active_key, provider, model_name, sel_label)


# ── Report ───────────────────────────────────────────────────────────────────
def _report(result: RunResult, session: Session, key: str, provider: str, model_name: Optional[str], label: str) -> None:
    c_btn, c_info = st.columns([1.2, 3], vertical_alignment="center")
    do = c_btn.button("Create analysis report", type="primary", key="ai_do_analyze", width="stretch")
    c_info.caption(
        f"Engine: {label}. Usually 3 to 15 seconds, one request. "
        "If it fails (quota, rate limit, outage), the next free engine answers automatically."
    )

    state_key = f"analysis_{result.run_id}_{provider}_{model_name}"
    engine_key = f"{provider}_{model_name}"
    data = st.session_state.get(state_key)
    from_disk = False
    if data is None and not do:
        data = load_analysis(result.run_id, engine_key)  # a saved report costs no API request
        if data:
            st.session_state[state_key] = data
            from_disk = True
    if do:
        payload = build_llm_payload(session, result)
        with st.spinner("Analysing consensus, trade-offs and risks…"):
            data = run_analysis(payload, api_key=key, provider=provider, model=model_name, keys=all_keys())
        st.session_state[state_key] = data
        if data.get("success"):
            try:
                save_analysis(result.run_id, engine_key, data)
            except OSError:
                pass

    if not data:
        callout("info", "Press the button above to create the report. It is saved with this run, so reopening it costs no API request.")
        return
    if not data.get("success"):
        callout("bad", str(data.get("error", "Unknown error")), "The report could not be created")
        return
    if from_disk:
        st.caption("Showing the report saved with this run (no API request used). Press the button to create a new one.")

    sections = data.get("sections", {})
    recom = sections.get("rekomendasi", {})
    if not isinstance(recom, dict):
        recom = {}
    winner = recom.get("alternative") or "Not stated"
    backup = recom.get("backup_alternative") or "Not stated"

    render_html(
        '<div class="stat-row">',
        f'<div class="stat"><div class="stat-label">AI recommendation</div><div class="stat-value" style="font-size:1.4rem">{esc(winner)}</div>'
        f'<div class="stat-hint">{esc(recom.get("based_on_model", ""))}</div></div>',
        f'<div class="stat"><div class="stat-label">Backup</div><div class="stat-value" style="font-size:1.4rem">{esc(backup)}</div></div>',
        f'<div class="stat"><div class="stat-label">Engine that answered</div><div class="stat-value" style="font-size:1.1rem;font-family:var(--f-body)">{esc(data.get("model_used", "-"))}</div></div>',
        "</div>",
    )
    unverified = data.get("unverified_numbers", [])
    if unverified:
        callout(
            "warn",
            "These decimal numbers appear in the report but were not found in the calculation results: " + ", ".join(map(str, unverified)),
            "Needs checking",
        )

    for note in data.get("notes", []):
        callout("info", str(note), "About this report")

    t1, t2, t3, t4, t5 = st.tabs(["Summary", "Across methods", "Strengths and weaknesses", "Risks and consistency", "Full document"])
    with t1:
        reasons = recom.get("reasons", [])
        if reasons:
            st.markdown("**Key reasons**")
            for r in reasons if isinstance(reasons, list) else [reasons]:
                st.markdown(f"- {r}")
        cond = recom.get("backup_condition")
        if cond:
            callout("info", str(cond), f"When to switch to {backup}")
        st.markdown(sections.get("ringkasan", "-"))
    with t2:
        st.markdown(sections.get("perbandingan", "-"))
    with t3:
        st.markdown(sections.get("kelebihan_kelemahan", "-"))
    with t4:
        st.markdown(sections.get("risiko", "-"))
        st.markdown("**Consistency of the assessments**")
        st.markdown(sections.get("konsistensi", "-"))
    with t5:
        md = data.get("markdown", "")
        st.markdown(md)
        st.download_button("Download analysis.md", data=md, file_name=f"analysis_{result.run_id}.md", mime="text/markdown", key="ai_dl_md")


# ── Chat ─────────────────────────────────────────────────────────────────────
def _chat(result: RunResult, session: Session, key: str, provider: str, model_name: Optional[str], label: str) -> None:
    run_id = result.run_id
    chat_key = f"active_chat_id_{run_id}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = f"chat-{uuid.uuid4().hex[:8]}"
    active = st.session_state[chat_key]

    c1, c2, c3 = st.columns([2.2, 1, 1], vertical_alignment="bottom")
    with c1:
        opts = [active] + [c for c in list_chats(run_id) if c != active]
        sel = st.selectbox("Conversation", options=opts, index=0, key=f"ai_chat_select_{run_id}")
        if sel != active:
            st.session_state[chat_key] = sel
            st.rerun()
    with c2:
        if st.button("New conversation", key=f"ai_new_chat_{run_id}", width="stretch"):
            st.session_state[chat_key] = f"chat-{uuid.uuid4().hex[:8]}"
            st.rerun()
    with c3:
        web = st.toggle("Search the web", value=False, key=f"ai_web_{run_id}", help="Adds web search results (DuckDuckGo) as context.")

    data = load_chat(run_id, active)
    history = data.get("messages", []) if data else []

    box = st.container(height=470)
    with box:
        if not history:
            st.markdown("Ask anything about this decision. A few examples:")
            for i, q in enumerate(_starter_questions(result, session)):
                if st.button(q, key=f"ai_starter_{i}_{active}", width="stretch"):
                    st.session_state[f"pending_prompt_{active}"] = q
                    st.rerun()
        else:
            for msg in history:
                with st.chat_message("user" if msg.get("role") == "user" else "assistant"):
                    st.markdown(msg.get("content", ""))
                    if msg.get("role") != "user":
                        _sources(msg.get("sources", []))
                        if msg.get("model_used"):
                            st.caption(f"Answered by {msg['model_used']}")

    pending = st.session_state.pop(f"pending_prompt_{active}", None)
    typed = st.chat_input("Write a question about this decision…", key=f"ai_chat_input_{active}")
    prompt = typed or pending
    if not prompt:
        return

    with box:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("The assistant is writing an answer…"):
                payload = build_llm_payload(session, result)
                summary = None
                for k, v in st.session_state.items():
                    if isinstance(k, str) and k.startswith(f"analysis_{run_id}") and isinstance(v, dict) and v.get("success"):
                        summary = v.get("sections", {}).get("ringkasan", "")
                        break
                reply, sources, model_used = chat_step(
                    run_id=run_id,
                    chat_id=active,
                    user_message=prompt,
                    payload=payload,
                    analysis_summary=summary,
                    enable_web_search=web,
                    api_key=key,
                    provider=provider,
                    model=model_name,
                    keys=all_keys(),
                )
            st.markdown(reply)
            _sources(sources)
            st.caption(f"Answered by {model_used}")
    st.rerun()
