import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from llm.client import call_llm, call_gemini, call_openrouter

print("=== 1. Testing Gemini ===")
content, used = call_gemini([{"role": "user", "content": "Reply briefly: Hello from the GDSS"}])
print(f"Result: {used} -> {content}")

print("\n=== 2. Testing OpenRouter ===")
content2, used2 = call_openrouter([{"role": "user", "content": "Reply briefly: Hello from the GDSS"}])
print(f"Result: {used2} -> {content2}")

print("\n=== 3. Testing call_llm (default) ===")
content3, used3 = call_llm([{"role": "user", "content": "Katakan: Sistem GDSS Siap Operasi!"}])
print(f"Result: {used3} -> {content3}")
