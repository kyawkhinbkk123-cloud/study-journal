# M5 Day 22 - Multi-agent system (Feynman own build: researcher + critic)
# Two agents collaborate: one drafts, one critiques -> better output.

import sys, json, re
sys.path.insert(0, ".")
import providers

def chat(msgs, system):
    resp = providers.chat(msgs, system=system)
    return resp["text"] if isinstance(resp, dict) else str(resp)

DRAFTER = "You are a concise technical writer. Answer in 2 sentences max."
CRITIC = ("You are a strict fact-checker. Given a question and a draft answer, "
          "reply ONLY JSON {\"ok\": true/false, \"fix\": \"<correction or empty>\"}.")

def multi_agent(question):
    # Agent 1: draft
    draft = chat([{"role": "user", "content": question}], DRAFTER)
    print("  DRAFTER:", draft[:100])
    # Agent 2: critique
    crit_msg = f"Question: {question}\nDraft: {draft}\nIs it correct?"
    crit = chat([{"role": "user", "content": crit_msg}], CRITIC)
    print("  CRITIC:", crit[:100])
    try:
        obj = json.loads(re.search(r"\{.*\}", crit, re.S).group(0))
    except Exception:
        return draft
    if obj.get("ok"):
        return draft
    # Agent 1 revises using critic feedback
    revise = chat([{"role": "user", "content": f"{question}\nFix this issue: {obj.get('fix','')}"}], DRAFTER)
    print("  REVISED:", revise[:100])
    return revise

if __name__ == "__main__":
    q = "What is the difference between DQN and PPO in one line each?"
    print("QUESTION:", q)
    print("FINAL:", multi_agent(q))
