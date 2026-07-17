# M4 Day 12 - Q-Learning table agent (Feynman own build: discretize + learn)

import gymnasium as gym
import numpy as np

env = gym.make("CartPole-v1")
n_bins = 10
# discretize 4D obs into bins -> state tuple
def discretize(obs):
    lo, hi = env.observation_space.low, env.observation_space.high
    hi[1], hi[3] = 3, 3  # clip velocity
    ratio = (np.array(obs) - lo) / (hi - lo)
    return tuple(np.clip((ratio * n_bins).astype(int), 0, n_bins - 1))

Q = np.zeros((n_bins,) * 4 + (2,))
lr, gamma, eps = 0.1, 0.99, 0.1

for ep in range(2000):
    obs, _ = env.reset()
    s = discretize(obs)
    done = False
    while not done:
        a = env.action_space.sample() if np.random.rand() < eps else int(np.argmax(Q[s]))
        nobs, r, term, trunc, _ = env.step(a)
        ns = discretize(nobs)
        Q[s + (a,)] += lr * (r + gamma * np.max(Q[ns]) - Q[s + (a,)])
        s, done = ns, (term or trunc)

# evaluate greedy
obs, _ = env.reset(); total = 0; done = False
while not done:
    a = int(np.argmax(Q[discretize(obs)]))
    obs, r, term, trunc, _ = env.step(a)
    total += r; done = term or trunc
env.close()
print("Q-learning greedy reward:", total, "(random was ~24)")
