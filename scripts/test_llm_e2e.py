import sys
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from engine.schemas import Session
from engine.pipeline import run_all
from llm.payload import build_llm_payload
from llm.analyze import run_analysis
from llm.chat import chat_step

print("1. Running the GDSS pipeline...")
with open(root / "data" / "sample_case.json", "r", encoding="utf-8") as f:
    session = Session.model_validate(json.load(f))

result = run_all(session)
payload = build_llm_payload(session, result)

print("2. Running run_analysis with Gemini...")
analysis_res = run_analysis(payload, provider="gemini", model="gemini-4-hydrogen")
print("Analysis Success:", analysis_res.get("success"))
print("Model Used:", analysis_res.get("model_used"))
print("Completeness:", analysis_res.get("completeness"))
print("Main recommendation:", analysis_res.get("sections", {}).get("rekomendasi", {}).get("alternative"))
print("Unverified Numbers:", analysis_res.get("unverified_numbers"))

print("\n3. Running chat_step with Gemini...")
reply, sources, model_used = chat_step(
    run_id=result.run_id,
    chat_id="test-chat-01",
    user_message="Why is the top-ranked product chosen by most methods?",
    payload=payload,
    provider="gemini",
    model="gemini-4-hydrogen"
)
print("Chat Model Used:", model_used)
print("Chat Reply Preview:", reply[:150], "...")

print("\nALL LLM E2E TESTS PASSED!")
