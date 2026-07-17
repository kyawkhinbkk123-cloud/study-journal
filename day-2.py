# M1 Day 2 - Functions deeper + NumPy intro (Feynman own examples)

import numpy as np

# --- Functions: default args, return multiple, lambda ---
def add_mul(a, b=2):
    return a + b, a * b

s, m = add_mul(5)
print("add_mul(5) ->", s, m)

square = lambda x: x ** 2
print("square(4) ->", square(4))

# --- NumPy: arrays beat lists for math ---
prices = np.array([100.0, 102.5, 99.0, 101.0])
print("mean:", prices.mean())
print("max-min spread:", prices.max() - prices.min())

# --- RL link: state can be a numpy vector ---
state = np.array([1.0, 0.0, -1.0])
print("state shape:", state.shape, "norm:", np.linalg.norm(state))
