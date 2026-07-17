# M4 Day 14 - REINFORCE / Policy Gradient from scratch (Feynman own build)
# DQN learns value; REINFORCE learns policy directly.

import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn

env = gym.make("CartPole-v1")
obs_dim = env.observation_space.shape[0]
n_act = env.action_space.n

class Policy(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, 128), nn.ReLU(),
            nn.Linear(128, n_act),
        )
    def forward(self, x):
        return torch.softmax(self.net(x), dim=-1)

pi = Policy()
opt = torch.optim.Adam(pi.parameters(), lr=1e-2)
gamma = 0.99

def run_episode():
    obs, _ = env.reset()
    log_probs, rewards = [], []
    done = False
    while not done:
        probs = pi(torch.tensor(obs, dtype=torch.float32))
        dist = torch.distributions.Categorical(probs)
        a = dist.sample()
        log_probs.append(dist.log_prob(a))
        obs, r, term, trunc, _ = env.step(int(a))
        rewards.append(r); done = term or trunc
    return log_probs, rewards

for ep in range(600):
    log_probs, rewards = run_episode()
    # discounted returns
    G, returns = 0, []
    for r in reversed(rewards):
        G = r + gamma * G
        returns.insert(0, G)
    returns = torch.tensor(returns)
    returns = (returns - returns.mean()) / (returns.std() + 1e-8)  # baseline
    loss = -torch.stack([lp * G for lp, G in zip(log_probs, returns)]).sum()
    opt.zero_grad(); loss.backward(); opt.step()

# evaluate greedy
rewards_eval = []
for _ in range(10):
    obs, _ = env.reset(); total = 0; done = False
    while not done:
        with torch.no_grad():
            a = int(pi(torch.tensor(obs, dtype=torch.float32)).argmax())
        obs, r, term, trunc, _ = env.step(a); total += r; done = term or trunc
    rewards_eval.append(total)
env.close()
print("REINFORCE avg reward (10 eval):", round(np.mean(rewards_eval), 1), "max:", max(rewards_eval))
print("(random ~24, Q-table ~156, DQN ~164)")
