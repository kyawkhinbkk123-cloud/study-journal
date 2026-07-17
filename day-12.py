# M4 Day 12 - Q-Learning table agent (Feynman own build: discretize + learn)

import gymnasium as gym
import numpy as np

env = gym.make("CartPole-v1")
n_bins = 10
# CartPole obs: [pos, vel, angle, ang_vel]; ranges are inf -> use manual bins
bins = [
    np.linspace(-2.4, 2.4, n_bins),    # cart position
    np.linspace(-3.0, 3.0, n_bins),    # cart velocity
    np.linspace(-0.3, 0.3, n_bins),    # pole angle
    np.linspace(-3.0, 3.0, n_bins),    # pole ang vel
]

def discretize(obs):
    return tuple(int(np.digitize(obs[i], bins[i]) - 1) for i in range(4))

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
