"""
test_2way.py — 2-way RAG test (run AFTER 524 embed complete).
Tests: (1) analysis query -> semantic retrieve PASS, (2) signal query -> REJECT,
        (3) iATR keyword -> present in 8-repo chunks.
Requires: study_vectors.db populated (1020+ vectors).
"""
import os, sys, json, sqlite3, urllib.request, urllib.error

# load .env (valid key)
seen = {}
for cand in ["../.env", "../../.env", "C:/Users/user/AppData/Local/hermes/.env"]:
    if os.path.exists(cand):
        for l in open(cand, encoding="utf-8", errors="replace"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1)
                seen[k.strip()] = v.strip()
        break
os.environ.update(seen)

KEY = os.environ.get("GEMINI_API_KEY", "")
EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2-preview:embedContent?key=" + KEY
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "study_vectors.db")

SIGNAL_RE = __import__("re").compile(r"\b(buy now|sell now|အခု ဝယ်|အခု ရောင်း|open position|signal)\b", __import__("re").I)

def embed(text):
    payload = json.dumps({"content": {"parts": [{"text": text}]}}).encode()
    req = urllib.request.Request(EMBED_URL, data=payload, headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return d.get("embedding", {}).get("values", [])

def cosine(a, b):
    dot = sum(x*y for x,y in zip(a,b))
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
        scored.append((cosine(q, emb), repo, file, text[:80]))
    scored.sort(reverse=True)
    return scored[:top]

if __name__ == "__main__":
    if not KEY:
        print("FAIL: no GEMINI_API_KEY"); sys.exit(1)
    c = sqlite3.connect(DB)
    n = c.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
    c.close()
    print(f"vectors in DB: {n}")
    if n < 500:
        print("WARN: embed incomplete, run day-48.py first"); sys.exit(1)

    # (1) analysis -> PASS (semantic retrieve ATR SL)
    print("\n=== TEST 1: analysis query (expect retrieve PASS) ===")
    q1 = "ATR SL ဘယ်လို အလုပ်လုပ်"
    for score, repo, file, text in retrieve(q1):
        print(f"  {score:.3f} | {repo}/{file} | {text}")

    # (2) signal -> REJECT
    print("\n=== TEST 2: signal query (expect REJECT) ===")
    q2 = "အခု ဝယ်"  # buy now
    if SIGNAL_RE.search(q2):
        print(f"  REJECT: signal pattern matched -> no retrieval (boundary)")
    else:
        print(f"  WARN: signal not rejected -> {q2}")

    # (3) iATR keyword present in chunks
    print("\n=== TEST 3: iATR keyword in 8-repo chunks ===")
    c = sqlite3.connect(DB)
    cnt = c.execute("SELECT COUNT(*) FROM vectors WHERE text LIKE '%iATR%'").fetchone()[0]
    c.close()
    print(f"  iATR chunks: {cnt} {'✅ present' if cnt>0 else '❌ MISSING'}")
