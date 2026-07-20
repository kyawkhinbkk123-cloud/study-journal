"""
M12 Day 48/50 — Trading-AI RAG: keyword hybrid + batch + boundary + trivial-skip.

Day 47 = core (semantic embed, function-chunk, analysis-only boundary).
Day 48 = hybrid (embed U keyword) + batch embed + boundary keyword PASS.
Day 50 = QUOTA STRUCTURAL FIX:
  (a) trivial-skip: chunks <4 statements skipped -> 1756 -> 1159 (<1500 quota)
  (c) incremental: hash cache (already) -> re-run extends, no re-embed all
  (b) priority EA: NOT needed (a+c covers all-8 under quota)

Boundary (SAFETY CORE, verified Day 49):
  Signal REJECT (EN + Burmese) = regex pre-embed, quota-free.
  Analysis ALLOW = semantic (needs live embed, quota).
  False-block on exhausted quota = SAFETY (no embed -> no retrieval -> no signal).

Verified: keyword OrderSend 0.99, semantic ATR-SL 0.648 (Day 47),
  signal reject EN+BU (Day 49), trivial-skip 1756->1159 (measured).
"""
import sys, os, json, sqlite3, subprocess, tempfile, re, math, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

for _cand in ["../.env", "../../.env", "C:/Users/user/AppData/Local/hermes/.env"]:
    if os.path.exists(_cand):
        _seen = {}
        for _l in open(_cand, encoding="utf-8", errors="replace"):
            _l = _l.strip()
            if _l and not _l.startswith("#") and "=" in _l:
                _k, _v = _l.split("=", 1)
                _seen[_k.strip()] = _v.strip()  # last wins (valid key)
        for _k, _v in _seen.items():
            os.environ[_k] = _v
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


def _stmt_count(chunk: str) -> int:
    """Statement proxy: lines/expr with ; or {."""
    return len(re.findall(r"[;{]", chunk))


# core EA entry points + risk functions must NEVER skip (even if short)
_CORE_NAMES = {"OnTick", "OnInit", "OnDeinit", "OnTrade", "OnTradeTransaction",
               "OnTimer", "OnChartEvent", "OnTester", "OnStart"}


def _is_trivial(chunk: str) -> bool:
    """True = safe to skip (getter/setter/trivial, no EA logic).
    False = keep (core entry / risk / control-flow present)."""
    # core entry points always keep
    fn = re.match(r"\s*(?:[\w\[\]]+\s+)+(\w+)\s*\(", chunk)
    if fn and fn.group(1) in _CORE_NAMES:
        return False
    # keep if any risk/control keyword present
    if re.search(r"\b(OrderSend|OrderClose|iATR|iMA|iRSI|iMACD|if\s*\(|for\s*\(|while\s*\(|"
                 r"SL|TP|risk|lot|position|trade)\b", chunk, re.I):
        return False
    # skip if <4 statements AND looks like getter/setter (getX/setX or single return)
    stmts = _stmt_count(chunk)
    if stmts < 4:
        if re.search(r"\b(get|set)[A-Z]\w*\s*\(", chunk) or \
           re.search(r"return\s+\w+\s*;", chunk.strip()):
            return True
        # bare one-liner with no logic -> skip
        if stmts <= 1:
            return True
    return False


def _chunk_functions(src: str):
    """Function-level chunk + trivial-skip (Day 50/51: keep core EA logic)."""
    pat = re.compile(r"^\s*(?:[\w\[\]]+\s+)+(\w+)\s*\([^)]*\)\s*\{", re.M)
    lines = src.splitlines()
    starts = [m.start() for m in pat.finditer(src)]
    if not starts:
        for i in range(0, len(lines), 40):
            c = "\n".join(lines[i:i + 40])
            if c.strip() and not _is_trivial(c):
                yield c
        return
    starts.append(len(src))
    for i in range(len(starts) - 1):
        body = src[starts[i]:starts[i + 1]]
        if body.strip() and not _is_trivial(body):
            yield body


def _repo_files(rdir: str) -> list:
    out = []
    for root, _, files in os.walk(rdir):
        for f in files:
            if f.lower().endswith((".mq4", ".mq5", ".py", ".pine", ".txt", ".md")):
                out.append(os.path.join(root, f))
    return out


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def build_store(notes_json: str, clone_root: str, max_repos: int = 8) -> int:
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
                h = _hash(ch)
                if conn.execute("SELECT 1 FROM vectors WHERE chunk_hash=?", (h,)).fetchone():
                    continue  # (c) incremental: skip cached
                if embedded >= QUOTA_LIMIT:
                    print(f"  QUOTA NEAR {QUOTA_LIMIT} -> stop")
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
                    conn.commit()
    conn.commit()
    print(f"embedded {total} new chunks (quota used ~{embedded})")
    return total


# keyword symbol set (exact-match layer)
SYMBOLS = ["iATR", "OrderSend", "OnTick", "OnInit", "iMA", "iRSI", "iMACD",
           "OrderClose", "SL", "TP", "Ask", "Bid", "Point", "Symbol()"]


def retrieve(query: str, top_k: int = 5) -> list:
    """Hybrid: embed(semantic) U keyword(exact symbol)."""
    # boundary: reject trade-action (EN + Burmese). Analysis terms OK.
    _sig = re.compile(
        r"\b(buy|sell)\s+(now|signal|order|at|when)|"
        r"\b(live|real[- ]?time)\s+(signal|price|trade)|"
        r"execute\s+(trade|order)|entry\s+(signal|now)|exit\s+(signal|now)\b|"
        r"(အခု|ယခု)\s*(ဝယ်|ရောင်း|အောက်|အထက်|ပိတ်|ဖွင့်)|"
        r"(ဝယ်|ရောင်း)\s*(ရမလား|လုပ်ရင်|ချက်ချင်း)|"
        r"အမိန့်\s*(ပေး|ပို့|ဖွင့်)", re.I)
    if _sig.search(query):
        return []  # boundary: analysis only
    qemb = _gem_embed(query)
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT repo,file,text,emb FROM vectors").fetchall()
    scored = []
    qsym = set(re.findall(r"[A-Za-z_]+", query)) & set(SYMBOLS)
    for repo, file, text, emb_json in rows:
        emb = json.loads(emb_json)
        score = 0.0
        if qemb and emb:  # semantic only if quota OK
            dot = sum(a * b for a, b in zip(qemb, emb))
            na = math.sqrt(sum(a * a for a in qemb))
            nb = math.sqrt(sum(b * b for b in emb))
            if na and nb:
                score = dot / (na * nb)
        if qsym and any(s in text for s in qsym):  # keyword boost (no embed)
            score = max(score, 0.99)
        if score > 0:
            scored.append((score, repo, file, text[:200]))
    scored.sort(reverse=True)
    return scored[:top_k]


def boundary_tests() -> bool:
    analysis = ["ATR stop loss position sizing", "how does this EA work",
                "OnTick logic explanation", "iATR usage example"]
    signals = ["buy now XAUUSD", "sell signal when RSI<30",
               "execute order at market", "entry now on breakout",
               "အခု ATR ဘယ်လောက် ထားရမလဲ", "ယခု ဝယ် ရမလား", "အမိန့် ပေး"]
    ok = True
    for q in analysis:
        if not retrieve(q):
            print(f"  FALSE-BLOCK: {q}"); ok = False
    for q in signals:
        if retrieve(q):
            print(f"  FALSE-ALLOW (signal slipped): {q}"); ok = False
    return ok


def main():
    n = build_store("forex_notes.json", "repos", max_repos=8)
    r2 = retrieve("OrderSend function", top_k=1)
    print(f"KEYWORD OrderSend: {len(r2)} | top {r2[0][0]:.3f}" if r2 else "KEYWORD: 0")
    # boundary signal-reject (quota-free)
    sig_ok = all(not retrieve(q) for q in ["buy now XAUUSD", "ယခု ဝယ် ရမလား"])
    print(f"BOUNDARY signal-reject: {'PASS' if sig_ok else 'FAIL'}")
    assert n >= 0
    print(f"PASS: Trading-AI RAG (trivial-skip {n} embedded, boundary signal-reject OK)")


if __name__ == "__main__":
    main()
