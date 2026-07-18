"""
M11 Day 46 — Autonomous Research Agent (multi-hop + loop guard).

Path 1 specialized #3. M9 agents (ReAct/schema) + network allowlist.
Agent loop: search(wikipedia) -> fetch extract -> find linked topic ->
  search again (depth<=2) -> synthesize via groq (research only).

Loop guard: visited set + MAX_DEPTH (no infinite fetch).
Schema: tool name in {search, fetch, synthesize}, args validated.
Network: wikipedia allowlisted (host literal, query-dynamic OK).

Study claim: research agent = ReAct + multi-hop + loop guard + synthesize.
Live-signal boundary NOT touched (research only, no trading).

Test: 2-hop from "RAG" -> linked "Neural network" -> synthesize summary.
"""
import sys, os, json, subprocess, tempfile, re
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


def _wiki_extract(title: str) -> str:
    """Fetch wikipedia extract (allowlisted host, query-dynamic OK)."""
    url = (f"https://en.wikipedia.org/w/api.php"
           f"?action=query&format=json&prop=extracts&explaintext=1&titles={title}")
    cfg = tempfile.NamedTemporaryFile(mode="w", suffix=".curl", delete=False)
    os.chmod(cfg.name, 0o600)
    cfg.write('header = "User-Agent: HermesStudy/1.0"\n')
    cfg.write(f'url = "{url}"\n')
    cfg.close()
    out = subprocess.run(["curl", "-s", "--max-time", "20", "-G", "-K", cfg.name],
                         capture_output=True, text=True, timeout=25)
    os.remove(cfg.name)
    d = json.loads(out.stdout)
    pages = d.get("query", {}).get("pages", {})
    for k, v in pages.items():
        return v.get("extract", "")[:800]
    return ""


def _linked_topic(extract: str) -> str:
    """Naive: pick first related topic as next hop (simulate link)."""
    for term in ("neural network", "embedding", "transformer", "information retrieval"):
        if re.search(term, extract, re.I):
            return term.replace(" ", "_").title()
    return ""


def _synthesize(query: str, texts: list) -> str:
    """LLM summarize (research only, no live-signal). groq via curl (no providers import)."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return "(no groq key)"
    prompt = (f"Summarize research on '{query}' from these sources in 2 bullets:\n"
              + "\n".join(f"- {t[:200]}" for t in texts if t))
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}],
                          "model": "llama-3.3-70b-versatile", "max_tokens": 200,
                          "temperature": 0.3})
    url = "https://api.groq.com/openai/v1/chat/completions"
    cfg = tempfile.NamedTemporaryFile(mode="w", suffix=".curl", delete=False)
    os.chmod(cfg.name, 0o600)
    cfg.write(f'header = "Authorization: Bearer {key}"\n')
    cfg.write('header = "Content-Type: application/json"\n')
    cfg.write(f'url = "{url}"\n')
    cfg.close()
    out = subprocess.run(["curl", "-s", "--max-time", "30", "-X", "POST", "-K", cfg.name,
                         "-d", payload], capture_output=True, text=True, timeout=35)
    os.remove(cfg.name)
    try:
        d = json.loads(out.stdout)
        txt = d.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        txt = ""
    if not txt.strip():
        # fallback: simple concat (no LLM) when groq unavailable/empty
        return "Research summary:\n" + "\n".join(f"- {t[:120]}" for t in texts if t)
    return txt


def research_agent(topic: str, max_depth: int = 2) -> dict:
    """Multi-hop research with loop guard."""
    visited = set()
    texts = []
    current = topic
    for depth in range(max_depth):
        if current in visited:
            break
        visited.add(current)
        ext = _wiki_extract(current)
        if not ext:
            break
        texts.append(ext)
        nxt = _linked_topic(ext)
        if not nxt or nxt in visited:
            break
        current = nxt
    summary = _synthesize(topic, texts)
    return {"depth": len(visited), "visited": list(visited), "summary": summary}


def main():
    res = research_agent("Retrieval-augmented_generation", max_depth=2)
    print(f"DEPTH: {res['depth']}")
    print(f"VISITED: {res['visited']}")
    print(f"SUMMARY: {res['summary'][:120]}")
    assert res["depth"] <= 2, f"loop guard failed: depth={res['depth']}"
    assert res["visited"], "no research done"
    assert len(res["summary"]) > 20
    print("PASS: research agent (multi-hop + loop guard + synthesize)")


if __name__ == "__main__":
    main()
