# M7 Day 25 - Advanced prompting: Chain-of-Thought vs direct (Feynman, real API)

import sys, re
sys.path.insert(0, ".")
import providers

def ask(prompt, system=None):
    resp = providers.chat([{"role": "user", "content": prompt}], system=system)
    return resp["text"] if isinstance(resp, dict) else str(resp)

# A reasoning problem where CoT should beat direct
PROBLEM = ("A trader starts with $1000. Day 1 he gains 20%. Day 2 he loses 20%. "
           "Day 3 he gains 20%. What is his final balance? Give only the final number.")

def extract_num(text):
    m = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    return m[-1] if m else "?"

# Direct
direct = ask(PROBLEM, system="Answer with only the final number, no working.")
# Chain-of-Thought
cot = ask(PROBLEM, system="Think step by step, show each day's calculation, then give the final number.")

print("DIRECT answer:", extract_num(direct))
print("CoT answer:", extract_num(cot))
print("CoT reasoning tail:", cot[-150:].replace(chr(10), " "))
# Correct: 1000*1.2=1200, *0.8=960, *1.2=1152
print("EXPECTED: 1152.0")
