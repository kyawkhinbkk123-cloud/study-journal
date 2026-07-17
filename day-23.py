# M5 Day 23 - ReAct planning agent (Feynman own build) - multi-step think-act-observe
# The formula's "think -> act -> observe" loop (Day15 deploy policy).

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
    "You are a ReAct agent. Solve step by step. Each turn reply ONLY JSON:\n"
    '{"thought":"...","tool":"calculator","arg":"<expr>"} to use a tool, OR\n'
    '{"thought":"...","answer":"<final>"} when done.\n'
    "Tool: calculator(math). Break multi-step math into steps."
)

def react_agent(task, max_steps=5):
    history = [{"role": "user", "content": task}]
    for step in range(max_steps):
        resp = providers.chat(history, system=SYSTEM, json_mode=True)
        reply = resp["text"] if isinstance(resp, dict) else str(resp)
        try:
            obj = json.loads(re.search(r"\{.*\}", reply, re.S).group(0))
        except Exception as e:
            return f"parse fail: {e}"
        print(f"  step {step+1} thought:", obj.get("thought", "")[:70])
        if "answer" in obj:
            return obj["answer"]
        if obj.get("tool") in TOOLS:
            result = TOOLS[obj["tool"]](obj.get("arg", ""))
            print(f"    -> {obj['tool']}({obj.get('arg')}) = {result}")
            history.append({"role": "assistant", "content": reply})
            history.append({"role": "user", "content": f"Observation: {result}"})
    return "max steps reached"

if __name__ == "__main__":
    task = "A trader buys 3 lots at 1850 and 2 lots at 1855. What is the total cost?"
    print("TASK:", task)
    print("FINAL:", react_agent(task))
