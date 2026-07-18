"""
M10 Day 43 — A/B model eval (deterministic judge, capstone).

Day 42 = cost tracking. Day 43 = quality compare: run SAME task on 2 providers,
score outputs with DETERMINISTIC metrics (no LLM judge -> quota/bias safe).
Winner gets routing bias. This upgrades Hermes provider selection from
"not dead" (Day 37) + "most budget" (Day 42) to "best quality".

Deterministic metrics (Day 33 coverage style):
  - valid_syntax: py_compile pass
  - has_symbol: expected function/class name present
  - structure: >= N bullet/code lines

Study claim: A/B with deterministic judge > LLM-judge (cheap, unbiased, replayable).
Test: groq vs mistral on same coding task -> score both -> pick winner.
"""
import sys, os, re, ast
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


def score_response(text: str, expect_symbol: str) -> dict:
    """Deterministic quality score (no LLM)."""
    sc = {"valid_syntax": False, "has_symbol": False, "lines": 0, "total": 0}
    # extract code block if present
    m = re.search(r"```(?:python)?\n(.*?)```", text, re.S)
    code = m.group(1) if m else text
    # 1. valid syntax
    try:
        ast.parse(code)
        sc["valid_syntax"] = True
    except SyntaxError:
        pass
    # 2. expected symbol
    sc["has_symbol"] = expect_symbol in code
    # 3. structure (code/comment lines)
    sc["lines"] = len([l for l in code.splitlines() if l.strip()])
    # total score
    sc["total"] = (sc["valid_syntax"] * 2 + sc["has_symbol"] * 2 +
                   min(sc["lines"], 10))
    return sc


def ab_eval(task: str, expect_symbol: str, providers_list=("groq", "mistral")) -> dict:
    import providers
    scores = {}
    for p in providers_list:
        try:
            r = providers.chat([{"role": "user", "content": task}],
                               prefer=p, max_tokens=400, temperature=0.2)
            scores[p] = score_response(r["text"], expect_symbol)
        except Exception as e:
            scores[p] = {"error": str(e)[:40], "total": -1}
    # winner = highest total
    valid = {k: v for k, v in scores.items() if v.get("total", -1) >= 0}
    winner = max(valid, key=lambda k: valid[k]["total"]) if valid else ""
    return {"scores": scores, "winner": winner}


def main():
    task = "Write a Python function 'fib(n)' that returns nth Fibonacci number."
    expect = "def fib"
    res = ab_eval(task, expect)
    print("SCORES:", {k: v["total"] for k, v in res["scores"].items()})
    print("WINNER:", res["winner"])
    # both should produce valid fib -> winner has highest score
    assert res["winner"], "no winner (both failed?)"
    assert res["scores"][res["winner"]]["valid_syntax"], "winner not valid syntax"
    assert res["scores"][res["winner"]]["has_symbol"], "winner missing fib symbol"
    print("PASS: A/B eval (deterministic judge) picks best-quality provider")


if __name__ == "__main__":
    main()
