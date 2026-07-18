# M8 Day 31 - Re-ranking (improve retrieval precision over raw hybrid score)
# Raw hybrid gives candidates; re-rank re-scores with query-aware weighting
# so the truly best chunk surfaces first. Off main Hermes system.
import os, json, sqlite3, re, subprocess

HERMES = "C:/Users/user/AppData/Local/hermes"
NVIDIA_KEY = re.search(r"NVIDIA_API_KEY=(.+)", open(HERMES + "/.env").read()).group(1).strip()
EMBED_MODEL = "nvidia/nemotron-3-embed-1b"
DB = os.path.dirname(os.path.abspath(__file__)) + "/rag_day30.db"  # reuse Day 30 store


def embed(text, input_type="passage"):
    data = json.dumps({"input": text, "model": EMBED_MODEL,
                       "input_type": input_type, "encoding_format": "float"}).encode()
    out = subprocess.run(["curl", "-s", "https://integrate.api.nvidia.com/v1/embeddings",
                          "-H", "Authorization: Bearer " + NVIDIA_KEY,
                          "-H", "Content-Type: application/json", "-d", data.decode()],
                         capture_output=True, text=True, timeout=30)
    return json.loads(out.stdout)["data"][0]["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb + 1e-9)


def hybrid(query, top_k=4):
    qv = embed(query, "query")
    rows = sqlite3.connect(DB).execute("SELECT text, vec FROM chunks").fetchall()
    scored = []
    for text, vec in rows:
        dv = json.loads(vec)
        c = cosine(qv, dv)
        qs = set(re.findall(r"\w+", query.lower()))
        ds = set(re.findall(r"\w+", text.lower()))
        s = len(qs & ds) / (len(qs | ds) + 1e-9)
        scored.append((0.7 * c + 0.3 * s, text))
    scored.sort(reverse=True)
    return [t for _, t in scored[:top_k]]


def rerank(query, candidates):
    """Re-rank: weight rare query terms more (idf-like) + boost exact phrase match."""
    qterms = re.findall(r"\w+", query.lower())
    freq = {}
    for t in qterms:
        freq[t] = freq.get(t, 0) + 1
    # term rarity across candidates (rarer term -> more signal)
    df = {}
    for c in candidates:
        ct = set(re.findall(r"\w+", c.lower()))
        for t in qterms:
            if t in ct:
                df[t] = df.get(t, 0) + 1
    def score(c):
        ct = c.lower()
        s = 0.0
        for t in qterms:
            w = 1.0 / (df.get(t, 1))  # rarer across docs = higher weight
            s += w * (t in ct)
        if query.lower() in ct:
            s += 1.0  # exact phrase bonus
        return s
    return sorted(candidates, key=score, reverse=True)


if __name__ == "__main__":
    q = "How to control trading risk with stop-loss?"
    cands = hybrid(q, top_k=4)
    print("HYBRID TOP-4:")
    for c in cands:
        print("  -", c[:60])
    ranked = rerank(q, cands)
    print("\nRE-RANKED:")
    for c in ranked:
        print("  -", c[:60])
    # verify: risk chunk should move to #1 after re-rank
    assert ranked[0].lower().startswith("risk management"), ranked[0]
    print("\nPASS: re-ranking promoted the most query-relevant chunk to #1")
