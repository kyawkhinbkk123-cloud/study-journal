"""
M9 Day 40 — Agent safety boundaries (guardrails): sandbox + schema + PITFALLS.

M9 capstone. Agent safety = 3 layers (Hermes does all 3):
  1. SANDBOX: untrusted code scan (BLOCKED_MODULES + py_compile + pyflakes)
  2. SCHEMA: reject unsafe action before exec (Day 37)
  3. PITFALLS: post-mortem memory — don't repeat known mistake

Study claim: safe agent = code-sandbox + action-schema + mistake-memory.
Test: (a) untrusted code blocked by sandbox, (b) unsafe action rejected by
schema, (c) known pitfall (eval in tool) flagged by PITFALLS check.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# verify.py is a TOOL (not study sandbox code) -> safe to import
try:
    import verify
    HAVE_VERIFY = True
except Exception:
    HAVE_VERIFY = False

_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env")
if not os.path.exists(_env):
    _env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(_env):
    for _l in open(_env, encoding="utf-8", errors="replace"):
        _l = _l.strip()
        if _l and not _l.startswith("#") and "=" in _l:
            _k, _v = _l.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


# ---- layer 1: sandbox (reuse verify.py tool) ---------------------------
def sandbox_check(code: str) -> tuple:
    if not HAVE_VERIFY:
        return True, "verify.py absent (layer-3 off)"
    hits = verify.verify_code(code)
    if hits["status"] == "blocked":
        return False, hits["detail"]
    return True, "clean"


# ---- layer 2: schema (Day 37) -------------------------------------------
SCHEMA = {
    "calc": lambda a: bool(re.fullmatch(r"[0-9+\-*/().\s]+", a)),
    "wiki": lambda a: bool(re.fullmatch(r"[a-z]+", a)),
}


def schema_check(name: str, args: str) -> tuple:
    if name not in SCHEMA:
        return False, f"unknown tool: {name}"
    if not SCHEMA[name](args):
        return False, f"bad args: {args!r}"
    return True, "ok"


# ---- layer 3: PITFALLS (known mistake memory) --------------------------
PITFALLS = {
    "eval-in-tool": "tool ထဲ eval() = sandbox risk (Day 36)",
}


def pitfall_check(code: str) -> list:
    found = []
    if re.search(r"\beval\s*\(", code) and "re.fullmatch" not in code:
        found.append("eval-in-tool")
    return found


def main():
    # (a) sandbox blocks untrusted code
    bad_code = "import os\nos.system('rm -rf /')"
    ok, detail = sandbox_check(bad_code)
    print(f"sandbox block: {not ok} | {detail[:40]}")
    assert not ok

    # (b) schema rejects unsafe action
    ok, detail = schema_check("evil", "x")
    print(f"schema reject: {not ok} | {detail}")
    assert not ok

    # (c) PITFALLS flags known mistake
    pf = pitfall_check("def tool_calc(e): return eval(e)")
    print(f"pitfall found: {pf}")
    assert "eval-in-tool" in pf

    # (d) safe code + safe action pass
    ok, _ = sandbox_check("x = 1\nprint(x)")
    assert ok
    ok, _ = schema_check("calc", "2*3")
    assert ok

    print("PASS: 3-layer guardrail (sandbox + schema + PITFALLS)")


if __name__ == "__main__":
    main()
