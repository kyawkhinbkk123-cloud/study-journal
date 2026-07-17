# M5 Day 21 - Vector DB (cache embeddings) - Feynman own build
# Day20 critique: don't recompute embeddings each query. Store them (mini vector DB).

import sys, json, subprocess, math, pathlib, sqlite3, time
sys.path.insert(0, ".")
import providers

def load_key():
    for l in pathlib.Path("../.env").read_text("utf-8", "replace").splitlines():
        if l.startswith("NVIDIA_API_KEY="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
NV_KEY = load_key()

def embed(text, input_type):
    payload = json.dumps({"input": [text], "model": "nvidia/nemotron-3-embed-1b",
                          "input_type": input_type, "encoding_format": "float"})
    out = subprocess.run(
        ["curl", "-s", "--max-time", "30", "-X", "POST",
         "https://integrate.api.nvidia.com/v1/embeddings",
         "-H", "Authorization: Bearer " + NV_KEY,
         "-H", "Content-Type: application/json", "-d", payload],
        capture_output=True, text=True).stdout
    return json.loads(out)["data"][0]["embedding"]

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return dot / (na*nb + 1e-8)

# --- Mini vector DB in SQLite ---
DB = "study_journal/vectors.db"
def init_db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS vecs (id INTEGER PRIMARY KEY, doc TEXT, emb TEXT)")
    c.commit(); c.close()

def index_docs(docs):
    c = sqlite3.connect(DB)
    n = c.execute("SELECT COUNT(*) FROM vecs").fetchone()[0]
    if n == 0:   # only embed once (cache)
        for d in docs:
            e = embed(d, "passage")
            c.execute("INSERT INTO vecs(doc, emb) VALUES (?,?)", (d, json.dumps(e)))
        c.commit()
        print("  indexed", len(docs), "docs (embeddings cached)")
    else:
        print("  using cached embeddings:", n, "docs")
    c.close()

def search(query):
    q = embed(query, "query")
    c = sqlite3.connect(DB)
    rows = c.execute("SELECT doc, emb FROM vecs").fetchall(); c.close()
    scored = [(cosine(q, json.loads(e)), d) for d, e in rows]
    scored.sort(reverse=True)
    return scored[0]

DOCS = [
    "Kyaw studies AI agents for 6 months; month 4 is reinforcement learning.",
    "PPO is used in RLHF and ChatGPT training.",
    "REINFORCE and A2C are policy gradient methods.",
    "The study journal lives in GitHub repo study-journal.",
]

if __name__ == "__main__":
    init_db(); index_docs(DOCS)
    t0 = time.time()
    score, doc = search("What algorithms are policy gradient?")
    print(f"  top (score {score:.3f}): {doc}")
    print(f"  search time: {time.time()-t0:.2f}s (cached, no re-embed of docs)")
    msgs = [{"role": "user", "content": f"Context: {doc}\nQ: What algorithms are policy gradient? Answer from context."}]
    resp = providers.chat(msgs)
    print("ANSWER:", (resp["text"] if isinstance(resp, dict) else str(resp))[:120])
