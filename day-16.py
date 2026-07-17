# M4 Day 16 - PPO from scratch (Feynman own build)
# PPO = A2C + clipped objective (prevents too-large policy updates). Used in RLHF/ChatGPT.

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
gamma, clip, epochs = 0.99, 0.2, 4

recent = []
for ep in range(1000):
    obs, _ = env.reset()
    states, actions, log_probs_old, rewards = [], [], [], []
    done = False
    while not done:
        st = torch.tensor(obs, dtype=torch.float32)
        probs, _ = ac(st)
        dist = torch.distributions.Categorical(probs)
        a = dist.sample()
        states.append(st); actions.append(a)
        log_probs_old.append(dist.log_prob(a).detach())
        obs, r, term, trunc, _ = env.step(int(a))
        rewards.append(r); done = term or trunc
    # returns
    G, returns = 0, []
    for r in reversed(rewards):
        G = r + gamma * G; returns.insert(0, G)
    returns = torch.tensor(returns, dtype=torch.float32)
    returns = (returns - returns.mean()) / (returns.std() + 1e-8)
    states = torch.stack(states); actions = torch.stack(actions)
    log_probs_old = torch.stack(log_probs_old)
    # PPO update: multiple epochs on same batch with clipping
    for _ in range(epochs):
        probs, values = ac(states)
        values = values.squeeze()
        dist = torch.distributions.Categorical(probs)
        log_probs = dist.log_prob(actions)
        ratio = torch.exp(log_probs - log_probs_old)
        adv = returns - values.detach()
        surr1 = ratio * adv
        surr2 = torch.clamp(ratio, 1 - clip, 1 + clip) * adv
        actor_loss = -torch.min(surr1, surr2).mean()
        critic_loss = nn.functional.mse_loss(values, returns)
        entropy = dist.entropy().mean()
        loss = actor_loss + 0.5 * critic_loss - 0.01 * entropy
        opt.zero_grad(); loss.backward(); opt.step()
    recent.append(sum(rewards))
    if len(recent) >= 30 and np.mean(recent[-30:]) >= 475:
        print(f"solved at ep {ep} (avg30={np.mean(recent[-30:]):.0f})"); break

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
print("PPO avg reward (10 eval):", round(np.mean(rewards_eval), 1), "max:", max(rewards_eval))
print("(random ~24, Q-table ~156, DQN ~164, A2C 425, REINFORCE 500)")
