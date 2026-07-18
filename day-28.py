# M7 Day 28 - Structured Output (JSON mode) for production LLM apps
# Production essential: force the model to return valid JSON we can parse reliably.
# Uses providers.chat(json_mode=True). No venv/system changes (off main Hermes system).
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import providers


def extract_structured(user_text: str) -> dict:
    messages = [{"role": "user", "content": user_text}]
    system = (
        "You are a support triage assistant. "
        "Return ONLY JSON with keys: priority (low|medium|high), "
        "category (billing|tech|account|other), and a one-line summary."
    )
    resp = providers.chat(messages, system=system, json_mode=True, temperature=0.1)
    text = resp["text"] if isinstance(resp, dict) else str(resp)
    provider = resp.get("provider") if isinstance(resp, dict) else "?"
    # providers may already return parsed JSON if json_mode supported; else parse text
    try:
        data = json.loads(text)
    except Exception:
        # fallback: strip markdown fences
        cleaned = text.strip().strip("`").replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
    return {"data": data, "provider": provider}


if __name__ == "__main__":
    out = extract_structured(
        "My subscription was charged twice and I can't log in to stop it!"
    )
    print("via:", out["provider"])
    print("parsed:", json.dumps(out["data"], indent=2))
    # assertions (verify)
    d = out["data"]
    assert set(d.keys()) >= {"priority", "category", "summary"}, d
    assert d["category"] in ("billing", "tech", "account", "other")
    assert d["priority"] in ("low", "medium", "high")
    print("PASS: structured JSON output parsed + validated")
