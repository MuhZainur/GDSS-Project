import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from llm.client import call_llm
from llm.websearch import search_web, format_search_results_for_llm
from app.repository import save_chat, load_chat


def get_chat_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "chat_system.md"
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            text = f.read()
            if "```" in text:
                parts = text.split("```")
                if len(parts) >= 2:
                    return parts[1].strip()
            return text
    return "You are a GDSS assistant. Help analyse the decision results politely and accurately."


def sanitize_chat_reply(text: str) -> str:
    """Cleans a chat reply so it is always natural markdown text, like ChatGPT / Gemini."""
    if not text:
        return ""
    clean = text.strip()
    answer_keys = ["answer", "response", "content", "reply", "jawaban", "ringkasan"]
    # Wrapped in ```json ... ```
    if clean.startswith("```json") and clean.endswith("```"):
        inner = clean[7:-3].strip()
        try:
            parsed = json.loads(inner)
            if isinstance(parsed, dict):
                for k in answer_keys:
                    if k in parsed:
                        return str(parsed[k]).strip()
        except Exception:
            pass
    # Starts with { and ends with }
    if clean.startswith("{") and clean.endswith("}"):
        try:
            parsed = json.loads(clean)
            if isinstance(parsed, dict):
                for k in answer_keys:
                    if k in parsed:
                        return str(parsed[k]).strip()
        except Exception:
            pass
    return clean


def chat_step(
    run_id: str,
    chat_id: str,
    user_message: str,
    payload: Dict[str, Any],
    analysis_summary: Optional[str] = None,
    enable_web_search: bool = False,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    keys: Optional[Dict[str, str]] = None,
) -> Tuple[str, List[Dict[str, str]], str]:
    """
    Runs one chat turn:
    - loads the earlier chat history if there is any
    - builds the context: system prompt, payload JSON, chat history
    - when enable_web_search is on: searches the web and adds the results
    - calls the LLM (selected engine first, then the fallback chain, see llm.client)
    - cleans the reply so it reads naturally
    - saves the conversation to storage
    Returns: (assistant reply, list of sources, engine that answered)
    """
    existing_chat = load_chat(run_id, chat_id)
    if not existing_chat:
        existing_chat = {
            "chat_id": chat_id,
            "run_id": run_id,
            "created_at": datetime.now().isoformat(),
            "title": user_message[:40] + ("..." if len(user_message) > 40 else ""),
            "messages": []
        }

    history = existing_chat.get("messages", [])

    # 1. First system message: the chat rules
    messages = [{"role": "system", "content": get_chat_system_prompt()}]

    # 2. Second system message: the decision data
    context_text = f"Decision results for run {run_id}:\n{json.dumps(payload, indent=2, ensure_ascii=False)}"
    if analysis_summary:
        context_text += f"\n\nAnalysis summary:\n{analysis_summary}"
    messages.append({"role": "system", "content": context_text})

    # 3. Chat history: the last 12 messages (older ones are condensed)
    if len(history) > 12:
        older_messages = history[:-12]
        summary_lines = [f"{m['role']}: {m['content'][:100]}..." for m in older_messages]
        older_summary = "Summary of earlier messages in this discussion:\n" + "\n".join(summary_lines)
        messages.append({"role": "system", "content": older_summary})
        recent_history = history[-12:]
    else:
        recent_history = history

    for m in recent_history:
        messages.append({"role": m["role"], "content": m["content"]})

    # 4. Web search when enabled
    sources = []
    if enable_web_search:
        results = search_web(user_message, max_results=5)
        sources = results
        if results:
            web_text = "LATEST WEB SEARCH RESULTS:\n" + format_search_results_for_llm(results)
            messages.append({"role": "system", "content": web_text})

    # 5. The latest user message
    messages.append({"role": "user", "content": user_message})

    # 6. Call the LLM
    attempts: List[str] = []
    raw_reply, model_used = call_llm(
        messages=messages,
        provider=provider,
        model=model,
        temperature=0.5,
        max_tokens=1500,
        api_key=api_key,
        keys=keys,
        attempts=attempts,
    )

    if not raw_reply:
        assistant_reply = f"Sorry, the assistant could not answer. {model_used}"
        model_used = "no engine answered"
    else:
        assistant_reply = sanitize_chat_reply(raw_reply)
        if attempts:
            model_used = f"{model_used} (the selected engine failed: {' '.join(attempts)})"

    # 7. Save the chat history
    ts = datetime.now().isoformat()
    existing_chat["messages"].append({
        "role": "user",
        "content": user_message,
        "ts": ts,
        "web_search": enable_web_search
    })
    existing_chat["messages"].append({
        "role": "assistant",
        "content": assistant_reply,
        "ts": ts,
        "model_used": model_used,
        "sources": sources
    })

    save_chat(run_id, chat_id, existing_chat)

    return assistant_reply, sources, model_used
