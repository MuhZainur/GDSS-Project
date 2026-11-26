"""Checks the current free OpenRouter models and compares them with the allowed list in llm/client.py."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm.client import OPENROUTER_FREE_MODELS  # noqa: E402


def check_free_models():
    url = "https://openrouter.ai/api/v1/models"
    print(f"Fetching the model list from {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GDSS-Model-Check/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            models = json.loads(resp.read().decode("utf-8")).get("data", [])
    except Exception as e:
        print(f"Gagal memeriksa model OpenRouter: {e}")
        return

    free = {}
    for m in models:
        p = m.get("pricing", {})
        try:
            if float(p.get("prompt", -1)) == 0 and float(p.get("completion", -1)) == 0:
                free[m["id"]] = m
        except (TypeError, ValueError):
            continue

    allowed = {m.id for m in OPENROUTER_FREE_MODELS}
    print(f"\n{len(free)} free models found. Allow-list status (>29B total, >=10B active):")
    for mid in sorted(allowed):
        print(f"  {'ADA     ' if mid in free else 'HILANG  '} {mid}")
    print("\nOther free models (not on the list; check their size in the description before adding):")
    for mid, m in sorted(free.items()):
        if mid not in allowed:
            print(f"  - {mid}: {(m.get('description') or '')[:110]!r}")


if __name__ == "__main__":
    check_free_models()
