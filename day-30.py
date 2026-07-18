# M8 Day 30 - RAG Foundation: embed + store + cosine retrieval (hybrid-ready)
# Uses NVIDIA embed (curl-only per memory) for dense vectors + simple keyword
# (sparse) overlap. Combines for retrieval. Off main Hermes system (own db file).
import sys, os, json, sqlite3, re, subprocess

HERMES = "C:/Users/user/AppData/Local/hermes"  # root, where .env lives (absolute to avoid ../ confusion)
ENVKEY = open(HERMES + "/.env").read()
import re as _re
NVIDIA_KEY = _re.search(r"NVIDIA_API_KEY=(.+)", ENVKEY).group(1).strip()
EMBED_MODEL = "nvidia/nemotron-3-embed-1b"
DIM = 2048
DB = os.path.dirname(os.path.abspath(__file__)) + "/rag_day30.db"


def embed(text: str, input_type="passage"):
    data = json.dumps({"input": text, "model": EMBED_MODEL,
                       "input_type": input_type, "encoding_format": "float"}).encode()
    out = subprocess.run(
        ["curl", "-s", "https://integrate.api.nvidia.com/v1/embeddings",
         "-H", "Authorization: Bearer " + NVIDIA_KEY,
         "-H", "Content-Type: application/json", "-d", data.decode()],
        capture_output=True, text=True, timeout=30)
    return json.loads(out.stdout)["data"][0]["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb + 1e-9)


def sparse_overlap(q, doc):
    qs = set(re.findall(r"\w+", q.lower()))
    ds = set(re.findall(r"\w+", doc.lower()))
    return len(qs & ds) / (len(qs | ds) + 1e-9)


def build_store(docs):
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY, text TEXT, vec TEXT)")
    con.execute("DELETE FROM chunks")
    for d in docs:
        vec = embed(d, "passage")
        con.execute("INSERT INTO chunks (text, vec) VALUES (?,?)", (d, json.dumps(vec)))
    con.commit()
    con.close()


def retrieve(query, top_k=2):
    qv = embed(query, "query")
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT text, vec FROM chunks").fetchall()
    con.close()
    scored = []
    for text, vec in rows:
        dv = json.loads(vec)
        score = 0.7 * cosine(qv, dv) + 0.3 * sparse_overlap(query, text)
        scored.append((score, text))
    scored.sort(reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    docs = [
        "Reinforcement learning trains agents via reward signals and environment interaction.",
        "RAG retrieves relevant documents then generates answers with a language model.",
        "FastAPI builds async HTTP APIs with automatic OpenAPI documentation.",
        "Risk management limits drawdown using position sizing and stop-loss rules.",
    ]
    build_store(docs)
    print("store built:", len(docs), "chunks")
    for q in ["How does RAG work?", "How to control trading risk?"]:
        top = retrieve(q)
        print("\nQ:", q)
        for s, t in top:
            print(f"  {s:.3f}  {t}")
    # verify
    r1 = retrieve("How does RAG work?")
    assert "RAG" in r1[0][1], r1
    r2 = retrieve("How to control trading risk?")
    assert "risk" in r2[0][1].lower(), r2
    print("\nPASS: dense+sparse hybrid retrieval returns relevant chunks")
