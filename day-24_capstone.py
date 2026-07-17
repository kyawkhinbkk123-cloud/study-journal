# M6 Day 24 - CAPSTONE: Study Assistant Agent (combines all 6 months)
# RAG (retrieve past notes) + tools + ReAct planning + memory. Deploy-ready structure.

import sys, json, re, subprocess, math, pathlib, sqlite3
sys.path.insert(0, ".")
import providers

def load_key(name):
    for l in pathlib.Path("../.env").read_text("utf-8", "replace").splitlines():
        if l.startswith(name + "="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
NV_KEY = load_key("NVIDIA_API_KEY")

def embed(text, input_type):
    payload = json.dumps({"input": [text], "model": "nvidia/nemotron-3-embed-1b",
                          "input_type": input_type, "encoding_format": "float"})
    out = subprocess.run(["curl", "-s", "--max-time", "30", "-X", "POST",
        "https://integrate.api.nvidia.com/v1/embeddings",
        "-H", "Authorization: Bearer " + NV_KEY,
        "-H", "Content-Type: application/json", "-d", payload],
        capture_output=True, text=True).stdout
    return json.loads(out)["data"][0]["embedding"]

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x*x for x in a))*math.sqrt(sum(y*y for y in b)) + 1e-8)

# --- TOOL 1: RAG over the real study.db notes (retrieve what Kyaw learned) ---
def recall_notes(query):
    c = sqlite3.connect("study.db")
    rows = c.execute("SELECT topic, recap_line FROM study_notes WHERE recap_line != '' ORDER BY id DESC LIMIT 12").fetchall()
    c.close()
    if not rows:
        return "no notes"
    q = embed(query, "query")
    scored = []
    for topic, recap in rows:
        e = embed(f"{topic}: {recap}", "passage")
        scored.append((cosine(q, e), f"{topic} - {recap}"))
    scored.sort(reverse=True)
    return scored[0][1]

# --- TOOL 2: calculator ---
def calculator(expr):
    try:
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"

TOOLS = {"recall_notes": recall_notes, "calculator": calculator}

SYSTEM = (
    "You are Kyaw's study assistant. Reply ONLY JSON per turn:\n"
    '{"thought":"...","tool":"recall_notes|calculator","arg":"..."} to act, OR\n'
    '{"thought":"...","answer":"..."} when done.\n'
    "recall_notes(topic) searches Kyaw's study notes. calculator(expr) does math."
)

def assistant(task, max_steps=5):
    history = [{"role": "user", "content": task}]
    for step in range(max_steps):
        resp = providers.chat(history, system=SYSTEM, json_mode=True)
        reply = resp["text"] if isinstance(resp, dict) else str(resp)
        try:
            obj = json.loads(re.search(r"\{.*\}", reply, re.S).group(0))
        except Exception as e:
            return f"parse fail: {e}"
        print(f"  step {step+1}:", obj.get("thought", "")[:70])
        if "answer" in obj:
            return obj["answer"]
        if obj.get("tool") in TOOLS:
            result = TOOLS[obj["tool"]](obj.get("arg", ""))
            print(f"    -> {obj['tool']} = {result[:80]}")
            history.append({"role": "assistant", "content": reply})
            history.append({"role": "user", "content": f"Observation: {result}"})
    return "max steps reached"

if __name__ == "__main__":
    task = "What did I learn about PPO in my studies?"
    print("TASK:", task)
    print("ANSWER:", assistant(task))
