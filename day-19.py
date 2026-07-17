# M5 Day 19 - Agent with memory (multi-turn conversation) - Feynman own build

import sys, json, re
sys.path.insert(0, ".")
import providers

def calculator(expr):
    try:
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"

TOOLS = {"calculator": calculator}

SYSTEM = (
    "You are a helpful agent with memory of the conversation. "
    "To use a tool reply ONLY JSON {\"tool\":\"calculator\",\"arg\":\"<expr>\"}. "
    "Otherwise reply {\"answer\":\"<text>\"}. Use earlier turns as context."
)

class MemoryAgent:
    def __init__(self):
        self.history = []   # list of {role, content}

    def ask(self, user_msg):
        self.history.append({"role": "user", "content": user_msg})
        resp = providers.chat(self.history, system=SYSTEM, json_mode=True)
        reply = resp["text"] if isinstance(resp, dict) else str(resp)
        try:
            obj = json.loads(re.search(r"\{.*\}", reply, re.S).group(0))
        except Exception as e:
            self.history.append({"role": "assistant", "content": reply})
            return f"(raw) {reply[:80]}"
        if "tool" in obj and obj["tool"] in TOOLS:
            result = TOOLS[obj["tool"]](obj.get("arg", ""))
            ans = f"[calc] {result}"
        else:
            ans = obj.get("answer", str(obj))
        self.history.append({"role": "assistant", "content": ans})
        return ans

if __name__ == "__main__":
    agent = MemoryAgent()
    turns = [
        "My name is Kyaw. Remember it.",
        "What is 15 * 12?",
        "What is my name?",   # tests memory
    ]
    for t in turns:
        print("USER:", t)
        print("AGENT:", agent.ask(t))
        print("-" * 40)
    print("history length:", len(agent.history))
