# M5 Day 18 - LLM tool-calling agent (Feynman own build, uses free providers.chat)
# Agent = LLM(brain) + Tools(hands). LLM decides which tool; Python runs it.

import sys, json, re
sys.path.insert(0, ".")
import providers

# --- Tools (hands) ---
def calculator(expr):
    try:
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"

def word_count(text):
    return str(len(text.split()))

TOOLS = {"calculator": calculator, "word_count": word_count}

SYSTEM = (
    "You are a tool-using agent. To use a tool, reply ONLY with JSON: "
    '{"tool": "<name>", "arg": "<argument>"}. '
    "Tools: calculator(math expression), word_count(text). "
    "If no tool needed, reply {\"answer\": \"<final answer>\"}."
)

def run_agent(user_msg):
    msgs = [{"role": "user", "content": user_msg}]
    resp = providers.chat(msgs, system=SYSTEM, json_mode=True)
    reply = resp["text"] if isinstance(resp, dict) else str(resp)
    print("  LLM raw:", reply[:120], "| via", resp.get("provider") if isinstance(resp, dict) else "?")
    try:
        m = re.search(r"\{.*\}", reply, re.S)
        obj = json.loads(m.group(0))
    except Exception as e:
        return f"parse fail: {e}"
    if "tool" in obj and obj["tool"] in TOOLS:
        result = TOOLS[obj["tool"]](obj.get("arg", ""))
        return f"[tool {obj['tool']}] -> {result}"
    return obj.get("answer", str(obj))

if __name__ == "__main__":
    for q in ["What is 23 * 47?", "How many words in 'the quick brown fox jumps'?"]:
        print("USER:", q)
        print("AGENT:", run_agent(q))
        print("-" * 40)
