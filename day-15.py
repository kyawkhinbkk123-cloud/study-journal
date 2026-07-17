# M4 Day 15 - Actor-Critic (A2C) TUNED (entropy + advantage normalize)

import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn

env = gym.make("CartPole-v1")
obs_dim = env.observation_space.shape[0]
n_act = env.action_space.n

class ActorCritic(nn.Module):
    def __init__(self):
        super().__init__()
        self.shared = nn.Sequential(nn.Linear(obs_dim, 128), nn.ReLU())
        self.actor = nn.Linear(128, n_act)
        self.critic = nn.Linear(128, 1)
    def forward(self, x):
        h = self.shared(x)
        return torch.softmax(self.actor(h), dim=-1), self.critic(h)

ac = ActorCritic()
opt = torch.optim.Adam(ac.parameters(), lr=3e-3)
gamma, ent_coef = 0.99, 0.01

recent = []
for ep in range(1000):
    obs, _ = env.reset()
    log_probs, values, rewards, entropies = [], [], [], []
    done = False
    while not done:
        probs, value = ac(torch.tensor(obs, dtype=torch.float32))
        dist = torch.distributions.Categorical(probs)
        a = dist.sample()
        log_probs.append(dist.log_prob(a)); values.append(value.squeeze())
        entropies.append(dist.entropy())
        obs, r, term, trunc, _ = env.step(int(a))
        rewards.append(r); done = term or trunc
    G, returns = 0, []
    for r in reversed(rewards):
        G = r + gamma * G; returns.insert(0, G)
    returns = torch.tensor(returns, dtype=torch.float32)
    returns = (returns - returns.mean()) / (returns.std() + 1e-8)  # normalize
    values = torch.stack(values)
    advantage = returns - values.detach()
    actor_loss = -(torch.stack(log_probs) * advantage).sum()
    critic_loss = nn.functional.mse_loss(values, returns)
    entropy = torch.stack(entropies).sum()
    loss = actor_loss + 0.5 * critic_loss - ent_coef * entropy  # entropy bonus
    opt.zero_grad(); loss.backward(); opt.step()
    recent.append(sum(rewards))
    if len(recent) >= 30 and np.mean(recent[-30:]) >= 475:
        print(f"solved at ep {ep} (avg30={np.mean(recent[-30:]):.0f})")
        break

rewards_eval = []
for _ in range(10):
    obs, _ = env.reset(); total = 0; done = False
    while not done:
        with torch.no_grad():
            probs, _ = ac(torch.tensor(obs, dtype=torch.float32))
            a = int(probs.argmax())
        obs, r, term, trunc, _ = env.step(a); total += r; done = term or trunc
    rewards_eval.append(total)
env.close()
print("A2C TUNED avg reward (10 eval):", round(np.mean(rewards_eval), 1), "max:", max(rewards_eval))
print("(random ~24, Q-table ~156, DQN ~164, REINFORCE 500)")
