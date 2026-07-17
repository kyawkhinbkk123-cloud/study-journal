# M1 Day 3 - Pandas data handling (Feynman own example: study journal log)

import pandas as pd

# Build a small study log (not copied - own data)
data = {
    "day": [1, 2, 3],
    "topic": ["Python basics", "Functions+NumPy", "Pandas"],
    "minutes": [90, 90, 90],
    "done": [True, True, False],
}
df = pd.DataFrame(data)
print(df)
print("--- total minutes studied:", df["minutes"].sum())
print("--- completed days:", df[df["done"]]["day"].tolist())

# RL/Agent link: a DataFrame can hold experience replay rows (state, action, reward)
exp = pd.DataFrame({
    "state": ["s1", "s2"],
    "action": ["buy", "hold"],
    "reward": [1.0, -0.5],
})
print("--- experience rows:", len(exp))
