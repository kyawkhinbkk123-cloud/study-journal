"""
M10 Day 42 — MLOps: cost/quota tracking.

Day 41 = drift monitor. Day 42 = cost/quota: rank providers by REMAINING
budget (cap - calls), skip cooldown, pick best for next call. Hermes free-tier
7 providers -> quota is the main constraint. provider_state already logs
calls/cap; Day 42 formalizes budget-aware selection.

Study claim: cost-aware routing = rank by remaining budget, not just "not dead".
Test: 3 providers w/ different calls -> selector picks highest remaining.
"""
import sys, os, json, time
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


def load_state():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "provider_state.json")
    if not os.path.exists(p):
        return {}
    return json.load(open(p, encoding="utf-8"))


def remaining(state: dict, name: str, cap: int = 150) -> int:
    s = state.get(name, {})
    return max(0, cap - s.get("calls", 0))


def best_provider(state: dict, order=("groq", "mistral", "openrouter", "cohere"),
                  cap: int = 150) -> str:
    """Pick provider with most remaining budget, skip cooldown."""
    now = time.time()
    ranked = []
    for name in order:
        s = state.get(name, {})
        if s.get("cooldown_until", 0) > now:
            continue
        ranked.append((remaining(state, name, cap), name))
    if not ranked:
        return ""
    ranked.sort(reverse=True)  # highest remaining first
    return ranked[0][1]


def budget_report(state: dict, cap: int = 150) -> dict:
    return {n: remaining(state, n, cap) for n in state}


def main():
    st = load_state()
    # simulate 3 providers different usage (don't touch real file)
    sim = dict(st)
    sim["groq"] = {"calls": 140, "cap": 150, "cooldown_until": 0}
    sim["mistral"] = {"calls": 30, "cap": 150, "cooldown_until": 0}
    sim["openrouter"] = {"calls": 10, "cap": 150, "cooldown_until": 0}

    rep = budget_report(sim)
    print(f"BUDGET: {rep}")
    best = best_provider(sim, order=("groq", "mistral", "openrouter"))
    print(f"BEST: {best}")
    # groq 140 left 10, mistral 120 left, openrouter 140 left -> openrouter wins
    assert best == "openrouter", f"should pick highest remaining, got {best}"
    assert remaining(sim, "openrouter") == 140

    # cooldown skip
    sim["openrouter"]["cooldown_until"] = time.time() + 9999
    best2 = best_provider(sim, order=("groq", "mistral", "openrouter"))
    print(f"BEST (openrouter cooled): {best2}")
    assert best2 == "mistral", f"cooled -> mistral, got {best2}"

    print("PASS: cost-aware routing (rank by remaining budget, skip cooldown)")


if __name__ == "__main__":
    main()
