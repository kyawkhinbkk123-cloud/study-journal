# M4 Day 17 - Custom Gymnasium env: simple trading env (Feynman own build)
# Ties RL to Kyaw's forex interest. Agent learns buy/hold/sell on a price series.

import gymnasium as gym
from gymnasium import spaces
import numpy as np

class TradingEnv(gym.Env):
    """State = [price_norm, position]. Actions: 0=hold, 1=buy, 2=sell. Reward = PnL."""
    def __init__(self, prices):
        super().__init__()
        self.prices = np.array(prices, dtype=np.float32)
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(low=-10, high=10, shape=(2,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.t = 0
        self.position = 0      # 0 = flat, 1 = long
        self.entry = 0.0
        return self._obs(), {}

    def _obs(self):
        p = self.prices[self.t]
        norm = (p - self.prices.mean()) / (self.prices.std() + 1e-8)
        return np.array([norm, self.position], dtype=np.float32)

    def step(self, action):
        price = self.prices[self.t]
        reward = 0.0
        if action == 1 and self.position == 0:      # buy
            self.position = 1; self.entry = price
        elif action == 2 and self.position == 1:    # sell
            reward = price - self.entry; self.position = 0
        self.t += 1
        done = self.t >= len(self.prices) - 1
        if done and self.position == 1:             # close at end
            reward += self.prices[self.t] - self.entry
        return self._obs(), reward, done, False, {}

# --- test with a rising then falling price series ---
prices = list(np.linspace(100, 120, 30)) + list(np.linspace(120, 105, 20))
env = TradingEnv(prices)

# smart policy: buy low, sell high (hand rule, verify env works)
obs, _ = env.reset(); total = 0; done = False
while not done:
    price_norm = obs[0]
    action = 1 if price_norm < -0.5 else (2 if price_norm > 0.8 else 0)
    obs, r, done, _, _ = env.step(action); total += r
print("custom trading env total PnL (rule agent):", round(total, 2))
print("env valid: obs_space", env.observation_space.shape, "actions", env.action_space.n)
