# M5 Day 20 - RAG with real NVIDIA embeddings (Feynman own build)
# Retrieval-Augmented Generation: embed docs -> cosine similarity -> feed top doc to LLM.
# NVIDIA embed quirk: urllib gets 500, MUST use curl (per memory).

import sys, json, subprocess, math, os, pathlib
sys.path.insert(0, ".")
import providers

def load_key():
    for l in pathlib.Path("../.env").read_text("utf-8", "replace").splitlines():
        if l.startswith("NVIDIA_API_KEY="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

NV_KEY = load_key()

def embed(text, input_type):
    payload = json.dumps({
        "input": [text], "model": "nvidia/nemotron-3-embed-1b",
        "input_type": input_type, "encoding_format": "float",
    })
    out = subprocess.run(
        ["curl", "-s", "--max-time", "30", "-X", "POST",
         "https://integrate.api.nvidia.com/v1/embeddings",
         "-H", "Authorization: Bearer " + NV_KEY,
         "-H", "Content-Type: application/json",
         "-d", payload],
        capture_output=True, text=True).stdout
    return json.loads(out)["data"][0]["embedding"]

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-8)

# Knowledge base (own docs about Kyaw's study)
DOCS = [
    "Kyaw is learning AI agents over 6 months, month 4 is reinforcement learning.",
    "PPO is the RL algorithm used in RLHF and ChatGPT training.",
    "The study journal is committed to GitHub repo study-journal.",
]

def rag_answer(question):
    q_emb = embed(question, "query")
    doc_embs = [embed(d, "passage") for d in DOCS]
    scores = [cosine(q_emb, de) for de in doc_embs]
    best = max(range(len(DOCS)), key=lambda i: scores[i])
    context = DOCS[best]
    print(f"  retrieved (score {scores[best]:.3f}): {context}")
    msgs = [{"role": "user", "content": f"Context: {context}\n\nQuestion: {question}\nAnswer using only the context."}]
    resp = providers.chat(msgs)
    return resp["text"] if isinstance(resp, dict) else str(resp)

if __name__ == "__main__":
    q = "Which RL algorithm is used in ChatGPT?"
    print("QUESTION:", q)
    print("RAG ANSWER:", rag_answer(q))
