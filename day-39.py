"""
M9 Day 39 — Agent observability: audit trail logger.

Day 36-38 built loop / schema / recovery. Day 39 = SEE what happened:
every tool call logged (ts, action, args, result, ok/fail) so you can replay
+ audit. Hermes __audit.py is the same idea at system level.

Study claim: observable agent logs every step, not just final answer.
Without trail, a bad tool call is invisible until output breaks.

Test: agent runs 2 tools, trail shows both with ts + status; replay reproduces.
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


class AuditTrail:
    def __init__(self):
        self.events = []

    def log(self, action: str, args: str, result: str, ok: bool):
        ev = {
            "ts": time.strftime("%H:%M:%S"),
            "action": action,
            "args": args,
            "result": result[:50],
            "ok": ok,
        }
        self.events.append(ev)
        return ev

    def replay(self) -> str:
        return "\n".join(
            f"[{e['ts']}] {e['action']}({e['args']!r}) -> {e['result']} "
            f"[{'OK' if e['ok'] else 'FAIL'}]"
            for e in self.events
        )

    def summary(self) -> dict:
        return {
            "calls": len(self.events),
            "fails": sum(1 for e in self.events if not e["ok"]),
        }


# mock tools
def tool_calc(expr: str) -> str:
    return str(eval(expr)) if __import__("re").fullmatch(r"[0-9+\-*/().\s]+", expr) else "ERR"


def tool_wiki(entity: str) -> str:
    return {"france": "Paris"}.get(entity, "UNKNOWN")


def main():
    trail = AuditTrail()
    # agent does 2 calls
    for action, args in [("calc", "2*3"), ("wiki", "france")]:
        tool = {"calc": tool_calc, "wiki": tool_wiki}[action]
        try:
            res = tool(args)
            ok = res != "ERR" and res != "UNKNOWN"
            trail.log(action, args, res, ok)
        except Exception as e:
            trail.log(action, args, str(e), False)
    print(trail.replay())
    s = trail.summary()
    print(f"SUMMARY: {s}")
    assert s["calls"] == 2 and s["fails"] == 0, "trail mismatch"
    # replay reproducible
    assert "calc('2*3')" in trail.replay()
    print("PASS: audit trail logs every step + replayable + summary")


if __name__ == "__main__":
    main()
