"""
trading_rag_service.py — W2 Trading-AI RAG (paper-only, 4-layer boundary)
Scope: SEPARATE venv service (not Hermes core). Run with venv_m13 python.
Layers:
  L1 input regex (signal reject, pre-embed)
  L2 architecture-guard (NO broker import path exists)
  L3 localhost-only bind (0.0.0.0 refused)
  L4 paper-const (LIVE=False, no live_order() function)
Run: venv_m13/Scripts/python.exe trading_rag_service.py
"""
import os, sys, json, sqlite3, re, urllib.request
# W2 L2 architecture-guard: clear inherited PYTHONPATH (Hermes core venv) so only real broker import fails
os.environ.pop("PYTHONPATH", None)
sys.path = [p for p in sys.path if "hermes-agent/venv" not in p]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "venv_m13", "Lib", "site-packages"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "scripts"))
DB = "C:/Users/user/AppData/Local/hermes/scripts/study_vectors.db"
# load .env (GEMINI_API_KEY) — venv does not inherit .env
_env = open("C:/Users/user/AppData/Local/hermes/.env", encoding="utf-8", errors="replace").read()
for line in _env.splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
KEY = os.environ.get("GEMINI_API_KEY", "")
EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2-preview:embedContent?key=" + KEY

# L1: input regex (signal reject)
SIGNAL_RE = re.compile(r"(buy now|sell now|အခု ဝယ်|အခု ရောင်း|open position|signal)", re.I)

# L4: paper-only constant (secondary; L2 makes order impossible)
LIVE = False  # never True in this service

# L2: architecture-guard — assert NO broker module importable
def _guard_no_broker():
    # only flag REAL broker/trading modules, not windows/UI libs
    broker_mods = ["MT5", "MetaTrader5", "MetaTrader"]
    for mod in broker_mods:
        try:
            __import__(mod)
            return False  # real broker path exists -> unsafe
        except Exception:
            pass
    return True  # no broker path -> safe

def embed(text):
    payload = json.dumps({"content": {"parts": [{"text": text}]}}).encode()
    req = urllib.request.Request(EMBED_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return d.get("embedding", {}).get("values", [])

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5
    nb = sum(x*x for x in b) ** 0.5
    return dot/(na*nb) if na and nb else 0

def retrieve(query, top=3):
    q = embed(query)
    c = sqlite3.connect(DB)
    rows = c.execute("SELECT repo,file,text,emb FROM vectors").fetchall()
    c.close()
    scored = []
    for repo, file, text, emb_json in rows:
        emb = json.loads(emb_json)
        scored.append((cosine(q, emb), repo, file, text[:120]))
    scored.sort(reverse=True)
    return scored[:top]

# FastAPI app
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
app = FastAPI()

@app.post("/query")
async def query(req: Request):
    # L1: regex block
    data = await req.json()
    q = data.get("query", "")
    if SIGNAL_RE.search(q):
        return JSONResponse({"error": "signal-rejected", "layer": "L1"},
                            status_code=403)
    # L2: architecture-guard
    if not _guard_no_broker():
        return JSONResponse({"error": "broker-path-detected", "layer": "L2"},
                            status_code=403)
    # L4: paper-only
    if LIVE:
        return JSONResponse({"error": "live-mode-disabled", "layer": "L4"},
                            status_code=403)
    # retrieve (analysis only)
    results = retrieve(q)
    return {"query": q, "results": results, "mode": "paper-analysis"}

if __name__ == "__main__":
    import uvicorn
    # L3: localhost-only bind
    uvicorn.run(app, host="127.0.0.1", port=8803)
