# M7 Day 29 - Provider Fallback + Graceful Error Handling (production essential)
# Teaches: when primary LLM provider fails, try the next; never crash the app.
# Pure learning script - does NOT patch providers.py (keeps off main Hermes system).
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import providers


def chat_with_fallback(messages, system=None, order=("openrouter", "mistral", "groq")):
    """Try providers in order; return first success or a safe error dict."""
    last_err = None
    for name in order:
        try:
            # providers.chat uses internal provider selection; emulate prefer
            resp = providers.chat(messages, system=system, prefer=name)
            if isinstance(resp, dict) and resp.get("text"):
                return {"ok": True, "text": resp["text"], "provider": resp.get("provider"), "tried": name}
        except Exception as e:
            last_err = f"{name}: {e}"
            continue
    return {"ok": False, "error": last_err or "all providers failed", "text": "Sorry, service unavailable."}


if __name__ == "__main__":
    # normal case
    r = chat_with_fallback(
        [{"role": "user", "content": "What is 2+2? answer in one word"}],
        system="be terse",
    )
    print("RESULT:", r)
    assert r["ok"] is True and len(r["text"]) > 0
    print("PASS: fallback wrapper returns a provider response")

    # forced-failure case: prove graceful handling when EVERY real call throws.
    # We monkeypatch providers.chat to always raise, so the wrapper must degrade.
    real_chat = providers.chat
    def _boom(*a, **k):
        raise RuntimeError("simulated total provider outage")
    providers.chat = _boom
    try:
        r2 = chat_with_fallback(
            [{"role": "user", "content": "hi"}],
            system="be terse",
            order=("openrouter", "mistral"),
        )
    finally:
        providers.chat = real_chat
    print("FORCED-FAIL RESULT:", r2)
    assert r2["ok"] is False and r2["text"] == "Sorry, service unavailable."
    print("PASS: graceful degradation when all providers fail")
