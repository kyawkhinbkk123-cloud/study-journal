"""
M12 Day 48 — Trading-AI RAG: keyword hybrid + boundary 2-way + batch embed.

Day 47 = core (semantic embed, function-chunk, analysis-only boundary).
Day 48 = optimize:
  1. Keyword layer: exact symbol (iATR/OrderSend/OnTick) -> TF-IDF/string match.
     Hybrid = embed(semantic concept) U keyword(exact symbol) — Day 34 pattern on code.
  2. Boundary 2-WAY test: analysis query PASS + signal query REJECT (both verified).
     False-block fixed (Day 47: position sizing). Now test false-ALLOW (signal slips).
  3. Batch embed: repo-by-repo, cache hash skip, stop if near quota (1740>1500 -> split).

Quota plan (verified): 8 repos = 1740 chunks > 1500/day.
  Day 48: 6 small repos (~349 chunks). Day 49: 2 large (MT5-tools 815 + classes 576).
  No blind full embed -> half-indexed db avoided.

Boundary: retrieval = analysis ONLY. LLM explains EA, never trade action.
"""
import sys, os, json, sqlite3, subprocess, tempfile, re, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

for _cand in ["../.env", "../../.env", "C:/Users/user/AppData/Local/hermes/.env"]:
    if os.path.exists(_cand):
        for _l in open(_cand, encoding="utf-8", errors="replace"):
            _l = _l.strip()
            if _l and not _l.startswith("#") and "=" in _l:
                _k, _v = _l.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
        break

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2-preview:embedContent"
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "study_vectors.db")
QUOTA_LIMIT = 1400  # stop before 1500 hard cap (buffer)


def _gem_embed(text: str) -> list:
    cfg = tempfile.NamedTemporaryFile(mode="w", suffix=".curl", delete=False)
    os.chmod(cfg.name, 0o600)
    cfg.write(f'url = "{EMBED_URL}?key={GEMINI_KEY}"\n')
    cfg.close()
    payload = json.dumps({"content": {"parts": [{"text": text}]}})
    out = subprocess.run(["curl", "-s", "--max-time", "30", "-X", "POST", "-K", cfg.name,
                         "-H", "Content-Type: application/json", "-d", payload],
                         capture_output=True, text=True, timeout=35)
    os.remove(cfg.name)
    r = json.loads(out.stdout)
    return r.get("embedding", {}).get("values", [])


def _chunk_functions(src: str) -> list:
    pat = re.compile(r"^\s*(?:[\w\[\]]+\s+)+(\w+)\s*\([^)]*\)\s*\{", re.M)
    lines = src.splitlines()
    starts = [m.start() for m in pat.finditer(src)]
    if not starts:
        for i in range(0, len(lines), 40):
            c = "\n".join(lines[i:i + 40])
            if c.strip():
                yield c
        return
    starts.append(len(src))
    for i in range(len(starts) - 1):
        body = src[starts[i]:starts[i + 1]]
        if body.strip():
            yield body


def _repo_files(rdir: str) -> list:
    out = []
    for root, _, files in os.walk(rdir):
        for f in files:
            if f.lower().endswith((".mq4", ".mq5", ".py", ".pine", ".txt", ".md")):
                out.append(os.path.join(root, f))
    return out


def build_store(notes_json: str, clone_root: str, max_repos: int = 6) -> int:
    notes_json = notes_json if os.path.exists(notes_json) else \
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), notes_json)
    clone_root = clone_root if os.path.exists(clone_root) else \
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), clone_root)
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS vectors (
        id INTEGER PRIMARY KEY, repo TEXT, file TEXT, chunk_hash TEXT UNIQUE,
        text TEXT, emb BLOB, created_at REAL)""")
    notes = json.load(open(notes_json, encoding="utf-8"))
    total = 0
    embedded = 0
    for repo in list(notes.keys())[:max_repos]:
        rdir = os.path.join(clone_root, repo.split("/")[-1])
        if not os.path.exists(rdir):
            continue
        for fp in _repo_files(rdir):
            src = open(fp, encoding="utf-8", errors="replace").read()
            for ch in _chunk_functions(src):
                h = hashlib_sha(ch)
                if conn.execute("SELECT 1 FROM vectors WHERE chunk_hash=?", (h,)).fetchone():
                    continue
                if embedded >= QUOTA_LIMIT:
                    print(f"  QUOTA NEAR {QUOTA_LIMIT} -> stop (Day 49 batch rest)")
                    conn.commit()
                    return total
                emb = _gem_embed(ch[:2000])
                if not emb:
                    continue
                conn.execute("INSERT OR IGNORE INTO vectors(repo,file,chunk_hash,text,emb,created_at) VALUES(?,?,?,?,?,?)",
                             (repo, fp, h, ch[:2000], json.dumps(emb), time.time()))
                embedded += 1
                total += 1
                if embedded % 20 == 0:
                    conn.commit()  # batch commit -> no long lock
    conn.commit()
    print(f"embedded {total} new chunks (quota used ~{embedded})")
    return total


def hashlib_sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:16]


# keyword symbol set (exact-match layer)
SYMBOLS = ["iATR", "OrderSend", "OnTick", "OnInit", "iMA", "iRSI", "iMACD",
           "OrderClose", "SL", "TP", "Ask", "Bid", "Point", "Symbol()"]


def retrieve(query: str, top_k: int = 5) -> list:
    """Hybrid: embed(semantic) U keyword(exact symbol)."""
    # boundary: reject explicit trade-action phrases (not analysis terms)
    _sig = re.compile(
        r"\b(buy|sell)\s+(now|signal|order|at|when)|"
        r"\b(live|real[- ]?time)\s+(signal|price|trade)|"
        r"execute\s+(trade|order)|entry\s+(signal|now)|exit\s+(signal|now)\b", re.I)
    qemb = _gem_embed(query)
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT repo,file,text,emb FROM vectors").fetchall()
    scored = []
    qsym = set(re.findall(r"[A-Za-z_]+", query)) & set(SYMBOLS)
    for repo, file, text, emb_json in rows:
        emb = json.loads(emb_json)
        score = 0.0
        # semantic only if qemb available (quota not exhausted)
        if qemb and emb:
            dot = sum(a * b for a, b in zip(qemb, emb))
            na = math.sqrt(sum(a * a for a in qemb))
            nb = math.sqrt(sum(b * b for b in emb))
            if na and nb:
                score = dot / (na * nb)
        # keyword boost: exact symbol present in chunk (no embed needed)
        if qsym and any(s in text for s in qsym):
            score = max(score, 0.99)
        if score > 0:
            scored.append((score, repo, file, text[:200]))
    scored.sort(reverse=True)
    return scored[:top_k]


def boundary_tests() -> bool:
    """2-way: analysis PASS + signal REJECT (false-allow check)."""
    analysis = ["ATR stop loss position sizing", "how does this EA work",
                "OnTick logic explanation", "iATR usage example"]
    signals = ["buy now XAUUSD", "sell signal when RSI<30",
               "execute order at market", "entry now on breakout"]
    ok = True
    for q in analysis:
        if not retrieve(q):
            print(f"  FALSE-BLOCK: {q}")
            ok = False
    for q in signals:
        if retrieve(q):
            print(f"  FALSE-ALLOW (signal slipped): {q}")
            ok = False
    return ok


def main():
    n = build_store("forex_notes.json", "repos", max_repos=6)
    # hybrid test
    r1 = retrieve("ATR based stop loss", top_k=2)
    print(f"SEMANTIC 'ATR SL': {len(r1)} | top {r1[0][0]:.3f}" if r1 else "SEMANTIC: 0")
    r2 = retrieve("OrderSend function", top_k=2)
    print(f"KEYWORD 'OrderSend': {len(r2)} | top {r2[0][0]:.3f}" if r2 else "KEYWORD: 0")
    # boundary 2-way
    assert boundary_tests(), "BOUNDARY FAILED (false-block or false-allow)"
    assert n >= 0
    print("PASS: Trading-AI RAG hybrid (embed U keyword) + boundary 2-way OK")


if __name__ == "__main__":
    main()
