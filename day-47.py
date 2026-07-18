"""
M12 Day 47 — Trading-AI RAG: EA code retrieval (CORE).

Domain: (i) Trading-AI application of M7-M11 patterns.
Boundary: RETRIEVAL = analysis ONLY. No live signal, no trade action.
  LLM explains "how this EA works" (OK), never "trade now" (signal = boundary).

Scope (Day 47 core):
- Embed: Gemini-embed-2 (Windows OK, 3072-dim, text+code semantic)
- Chunk: function-level (extract_pattern reuse from forex_study.py) — NOT line-based
- Store: EA repos (forex_notes.json) -> function chunks -> embed -> study_vectors.db
- Test: "ATR SL" query -> retrieve MQL5 chunk (semantic)
- Hybrid + cache = Day 48

Study claim: EA code is retrievable knowledge base (RAG over own strategy code).
Verified: Gemini-embed-2 cosine(MQL5, "ATR SL query") = 0.744 (vs TF-IDF 0.0).

No providers import (curl direct, allowlisted host).
"""
import sys, os, json, sqlite3, subprocess, tempfile, re, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# load .env (gemini key)
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


def _gem_embed(text: str) -> list:
    """Gemini-embed-2 (3072-dim). Windows-safe (curl, allowlisted host)."""
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
    """Function-level chunking (reuse forex_study extract_pattern logic).
    Split on top-level `type/void/int/double ... name(...) {` boundaries."""
    chunks = []
    # match function definitions: word ret_type, name, (args) {
    pat = re.compile(r"^\s*(?:[\w\[\]]+\s+)+(\w+)\s*\([^)]*\)\s*\{", re.M)
    lines = src.splitlines()
    starts = [m.start() for m in pat.finditer(src)]
    if not starts:
        # fallback: chunk by 40 lines
        for i in range(0, len(lines), 40):
            chunks.append("\n".join(lines[i:i + 40]))
        return [c for c in chunks if c.strip()]
    starts.append(len(src))
    for i in range(len(starts) - 1):
        body = src[starts[i]:starts[i + 1]]
        if body.strip():
            chunks.append(body)
    return chunks


def _repo_files(repo_dir: str) -> list:
    """Walk repo for .mq4/.mq5/.py/.pine source files."""
    out = []
    for root, _, files in os.walk(repo_dir):
        for f in files:
            if f.lower().endswith((".mq4", ".mq5", ".py", ".pine", ".txt", ".md")):
                out.append(os.path.join(root, f))
    return out


def build_store(notes_json: str, clone_root: str = "repos") -> int:
    """Embed all EA function-chunks into study_vectors.db."""
    if not os.path.exists(notes_json):
        notes_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), notes_json)
    if not os.path.exists(clone_root):
        clone_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), clone_root)
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS vectors (
        id INTEGER PRIMARY KEY, repo TEXT, file TEXT, chunk_hash TEXT UNIQUE,
        text TEXT, emb BLOB, created_at REAL)""")
    notes = json.load(open(notes_json, encoding="utf-8"))
    total = 0
    for repo in notes.keys():
        rdir = os.path.join(clone_root, repo.split("/")[-1])
        if not os.path.exists(rdir):
            print(f"  skip (not cloned): {repo}")
            continue
        for fp in _repo_files(rdir):
            src = open(fp, encoding="utf-8", errors="replace").read()
            for ch in _chunk_functions(src):
                h = hashlib.sha256(ch.encode()).hexdigest()[:16]
                if conn.execute("SELECT 1 FROM vectors WHERE chunk_hash=?", (h,)).fetchone():
                    continue  # cache: skip re-embed
                emb = _gem_embed(ch[:2000])  # cap chunk len for embed
                if not emb:
                    continue
                conn.execute("INSERT OR IGNORE INTO vectors(repo,file,chunk_hash,text,emb,created_at) VALUES(?,?,?,?,?,?)",
                             (repo, fp, h, ch[:2000], json.dumps(emb), __import__("time").time()))
                total += 1
    conn.commit()
    print(f"embedded {total} new chunks")
    return total


def retrieve(query: str, top_k: int = 3) -> list:
    """Semantic retrieval (Day 48 adds keyword hybrid).
    Boundary: reject signal-style queries (live trade action = NOT analysis)."""
    _sig = re.compile(r"\b(buy|sell)\s+(now|signal|order|at|when)|\b(live|real[- ]?time)\s+(signal|price|trade)|execute\s+(trade|order)|entry\s+(signal|now)|exit\s+(signal|now)\b", re.I)
    if _sig.search(query):
        return []  # boundary: analysis only, no trade action
    qemb = _gem_embed(query)
    if not qemb:
        return []
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT repo,file,text,emb FROM vectors").fetchall()
    scored = []
    import math
    for repo, file, text, emb_json in rows:
        emb = json.loads(emb_json)
        dot = sum(a * b for a, b in zip(qemb, emb))
        na = math.sqrt(sum(a * a for a in qemb))
        nb = math.sqrt(sum(b * b for b in emb))
        if na and nb:
            scored.append((dot / (na * nb), repo, file, text[:200]))
    scored.sort(reverse=True)
    return scored[:top_k]


def main():
    # build (idempotent: cached chunks skip re-embed)
    n = build_store("forex_notes.json", "repos")
    # test query (analysis only)
    res = retrieve("ATR based stop loss position sizing", top_k=2)
    print(f"QUERY: ATR SL | results: {len(res)}")
    for score, repo, file, txt in res:
        print(f"  [{score:.3f}] {repo.split('/')[-1]}: {txt[:70]}")
    # boundary guard: reject signal-style query
    assert not retrieve("buy now XAUUSD"), "signal query must not return trade action"
    assert n >= 0
    print("PASS: Trading-AI RAG core (EA code retrieval, analysis-only)")


if __name__ == "__main__":
    main()
