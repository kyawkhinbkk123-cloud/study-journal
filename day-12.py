# M4 Day 12 - Q-Learning TUNED (beat random properly)

import gymnasium as gym
import numpy as np

env = gym.make("CartPole-v1")
n_bins = 12
bins = [
    np.linspace(-2.4, 2.4, n_bins),
    np.linspace(-3.0, 3.0, n_bins),
    np.linspace(-0.21, 0.21, n_bins),
    np.linspace(-3.5, 3.5, n_bins),
]

def discretize(obs):
    return tuple(int(np.digitize(obs[i], bins[i]) - 1) for i in range(4))

Q = np.zeros((n_bins,) * 4 + (2,))
lr, gamma = 0.1, 0.99
eps, eps_min, eps_decay = 1.0, 0.05, 0.9995

EPISODES = 20000
for ep in range(EPISODES):
    obs, _ = env.reset()
    s = discretize(obs)
    done = False
    while not done:
        a = env.action_space.sample() if np.random.rand() < eps else int(np.argmax(Q[s]))
        nobs, r, term, trunc, _ = env.step(a)
        ns = discretize(nobs)
        done = term or trunc
        target = r + (0 if done else gamma * np.max(Q[ns]))
        Q[s + (a,)] += lr * (target - Q[s + (a,)])
        s = ns
    eps = max(eps_min, eps * eps_decay)

# evaluate greedy over 20 episodes
rewards = []
for _ in range(20):
    obs, _ = env.reset(); total = 0; done = False
    while not done:
        a = int(np.argmax(Q[discretize(obs)]))
        obs, r, term, trunc, _ = env.step(a)
        total += r; done = term or trunc
    rewards.append(total)
env.close()
print("Q-learning avg reward (20 eval):", round(np.mean(rewards), 1))
print("max:", max(rewards), "min:", min(rewards), "(random was ~24)")
