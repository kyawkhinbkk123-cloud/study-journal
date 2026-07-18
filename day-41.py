"""
M10 Day 41 — MLOps: model monitoring + drift detection + scheduled deploy.

M8 (RAG) + M9 (Agents) built the system. M10 = operate it:
  1. MONITOR: provider success rate / calls / cooldown (Hermes provider_state)
  2. DRIFT: when a provider hits cap, fallback chain kicks in (Day 37)
  3. DEPLOY: scheduled job runs pipeline on cron (Hermes cron = this)

Study claim: MLOps = monitor + drift-response + scheduled-deploy.
The infra already exists in Hermes; M10 formalizes it.

Test: simulate provider_state with groq near cap -> monitor flags drift,
fallback chain (groq->mistral) activates, cron would redeploy next tick.
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


def monitor_drift(state: dict, cap: int = 150) -> list:
    """Flag providers near/at cap (drift risk)."""
    alerts = []
    for name, s in state.items():
        calls = s.get("calls", 0)
        if calls >= cap:
            alerts.append(f"{name}: AT CAP ({calls}/{cap}) -> drift")
        elif calls >= cap * 0.8:
            alerts.append(f"{name}: near cap ({calls}/{cap}) -> watch")
    return alerts


def fallback_chain(state: dict, order=("groq", "mistral", "openrouter"), cap: int = 150) -> str:
    """Pick first provider not near cap / not in cooldown.
    Near cap = >=80% (proactive drift avoid, not just hard cap)."""
    now = time.time()
    for name in order:
        s = state.get(name, {})
        if s.get("calls", 0) >= cap * 0.8:   # proactive: near cap = drift risk
            continue
        if s.get("cooldown_until", 0) > now:
            continue
        return name
    return ""


def simulate_cron_redeploy(alerts: list) -> str:
    """Cron would re-route traffic away from drifted provider next tick."""
    if alerts:
        return "cron: next tick reroutes to fallback (drift handled)"
    return "cron: all healthy, no action"


def main():
    st = load_state()
    # inject groq near cap to simulate drift (don't touch real file)
    sim = dict(st)
    sim["groq"] = {"calls": 148, "cap": 150, "cooldown_until": 0, "last_error": ""}
    sim["mistral"] = {"calls": 20, "cap": 150, "cooldown_until": 0, "last_error": ""}

    alerts = monitor_drift(sim)
    print("ALERTS:", alerts)
    assert any("near cap" in a for a in alerts), "should flag groq near cap"

    active = fallback_chain(sim)
    print(f"ACTIVE PROVIDER: {active}")
    assert active == "mistral", "groq near cap -> mistral fallback"

    deploy = simulate_cron_redeploy(alerts)
    print(f"DEPLOY: {deploy}")
    assert "reroutes" in deploy

    print("PASS: MLOps monitor+drift+fallback (groq cap -> mistral, cron reroute)")


if __name__ == "__main__":
    main()
