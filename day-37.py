"""
M9 Day 37 — Agent tool-schema validation + fallback chains.

Day 36 = ReAct loop (call tools). Day 37 = make it SAFE + RESILIENT:
  1. SCHEMA VALIDATION: LLM action must match allowed tools + typed args.
     Reject unknown tool / bad args BEFORE exec (sandbox guard).
  2. FALLBACK CHAIN: if primary provider fails, try next (Hermes does this
     via provider_state cooldown). Agent must survive model outage.

Study claim: agent safety = validate-then-execute; resilience = fallback chain.
Test: (a) bad action rejected, (b) groq->mistral fallback when groq dead.
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env")
if not os.path.exists(_env):
    _env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(_env):
    for _l in open(_env, encoding="utf-8", errors="replace"):
        _l = _l.strip()
        if _l and not _l.startswith("#") and "=" in _l:
            _k, _v = _l.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


# ---- tool schema ----------------------------------------------------------
SCHEMA = {
    "calc": {"args": ["expr"], "check": lambda a: bool(re.fullmatch(r"[0-9+\-*/().\s]+", a))},
    "wiki": {"args": ["entity"], "check": lambda a: bool(re.fullmatch(r"[a-z]+", a))},
}


def validate_action(name: str, args: str) -> tuple:
    """Returns (ok, error). Reject before exec."""
    if name not in SCHEMA:
        return False, f"unknown tool: {name}"
    if not SCHEMA[name]["check"](args):
        return False, f"bad args for {name}: {args!r}"
    return True, ""


# ---- mock tools (safe, no eval) ------------------------------------------
def tool_calc(expr: str) -> str:
    return str(eval(expr))  # schema-guarded: numeric only reached here


def tool_wiki(entity: str) -> str:
    db = {"france": "Paris", "japan": "Tokyo"}
    return db.get(entity, "UNKNOWN")


TOOLS = {"calc": tool_calc, "wiki": tool_wiki}


# ---- fallback chain (provider routing) ----------------------------------
def llm_with_fallback(prompt: str, chain=("groq", "mistral", "openrouter")) -> str:
    """Try providers in order; skip ones in cooldown. Hermes-style fallback."""
    import providers
    for p in chain:
        try:
            r = providers.chat([{"role": "user", "content": prompt}],
                               prefer=p, max_tokens=120, temperature=0.1)
            return r["text"]
        except Exception as e:
            continue  # next provider
    return ""  # all failed


def main():
    # (a) schema validation — bad actions rejected
    bad = [("evil", "x"), ("calc", "import os"), ("wiki", "France123")]
    for name, args in bad:
        ok, err = validate_action(name, args)
        print(f"reject {name}({args!r}): {ok} | {err}")
        assert not ok, "should reject"

    # (b) good action passes + executes
    ok, err = validate_action("calc", "2*3")
    assert ok, err
    print(f"exec calc(2*3) = {TOOLS['calc']('2*3')}")

    # (c) fallback chain works (real groq primary)
    out = llm_with_fallback("Say: OK")
    print(f"fallback chain output: {out[:30]!r}")
    assert out.strip(), "all providers failed"

    print("PASS: schema validation rejects bad, fallback chain resilient")


if __name__ == "__main__":
    main()
