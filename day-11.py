# M4 Day 11 - RL: Gymnasium CartPole (Feynman: random agent first)

import gymnasium as gym

env = gym.make("CartPole-v1")
obs, info = env.reset(seed=42)
total_reward = 0
for step in range(200):
    action = env.action_space.sample()  # random policy
    obs, reward, terminated, truncated, info = env.step(action)
    total_reward += reward
    if terminated or truncated:
        obs, info = env.reset()
        break
env.close()
print("random agent total reward:", total_reward)
print("obs space:", env.observation_space.shape, "action space:", env.action_space.n)

# RL core: State(obs) -> Action -> Reward -> loop. Random = no learning yet.
