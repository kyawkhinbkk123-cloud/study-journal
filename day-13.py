# M4 Day 13 - DQN from scratch in PyTorch (SB3 broken: tensorflow conflict)
# Study role: build own instead of depending on broken lib.

import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import random
from collections import deque

env = gym.make("CartPole-v1")
obs_dim = env.observation_space.shape[0]
n_act = env.action_space.n

class QNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, 64), nn.ReLU(),
            nn.Linear(64, 64), nn.ReLU(),
            nn.Linear(64, n_act),
        )
    def forward(self, x):
        return self.net(x)

q = QNet(); target = QNet(); target.load_state_dict(q.state_dict())
opt = torch.optim.Adam(q.parameters(), lr=1e-3)
buf = deque(maxlen=10000)
gamma, bs = 0.99, 64
eps, eps_min, eps_decay = 1.0, 0.05, 0.995

def act(state, eps):
    if random.random() < eps:
        return env.action_space.sample()
    with torch.no_grad():
        return int(q(torch.tensor(state, dtype=torch.float32)).argmax())

for ep in range(400):
    obs, _ = env.reset(); done = False
    while not done:
        a = act(obs, eps)
        nobs, r, term, trunc, _ = env.step(a)
        done = term or trunc
        buf.append((obs, a, r, nobs, done))
        obs = nobs
        if len(buf) >= bs:
            batch = random.sample(buf, bs)
            s, aa, rr, ns, dd = zip(*batch)
            s = torch.tensor(np.array(s), dtype=torch.float32)
            aa = torch.tensor(aa).unsqueeze(1)
            rr = torch.tensor(rr, dtype=torch.float32).unsqueeze(1)
            ns = torch.tensor(np.array(ns), dtype=torch.float32)
            dd = torch.tensor(dd, dtype=torch.float32).unsqueeze(1)
            qval = q(s).gather(1, aa)
            with torch.no_grad():
                tgt = rr + gamma * target(ns).max(1, keepdim=True)[0] * (1 - dd)
            loss = nn.functional.mse_loss(qval, tgt)
            opt.zero_grad(); loss.backward(); opt.step()
    eps = max(eps_min, eps * eps_decay)
    if ep % 50 == 0:
        target.load_state_dict(q.state_dict())

# evaluate
rewards = []
for _ in range(10):
    obs, _ = env.reset(); total = 0; done = False
    while not done:
        a = act(obs, 0.0)
        obs, r, term, trunc, _ = env.step(a); total += r; done = term or trunc
    rewards.append(total)
env.close()
print("DQN avg reward (10 eval):", round(np.mean(rewards), 1), "max:", max(rewards))
print("(random ~24, Q-table ~156)")
