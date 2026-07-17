# M3 Day 9 - Simple Neural Network (Feynman own build: XOR)

import torch
import torch.nn as nn

# XOR: NN learns non-linear mapping (classic DL test)
X = torch.tensor([[0,0],[0,1],[1,0],[1,1]], dtype=torch.float32)
y = torch.tensor([[0],[1],[1],[0]], dtype=torch.float32)

model = nn.Sequential(
    nn.Linear(2, 4),
    nn.ReLU(),
    nn.Linear(4, 1),
    nn.Sigmoid(),
)
opt = torch.optim.SGD(model.parameters(), lr=0.1)
loss_fn = nn.BCELoss()

for epoch in range(2000):
    opt.zero_grad()
    pred = model(X)
    loss = loss_fn(pred, y)
    loss.backward()
    opt.step()

print("predictions:\n", model(X).round().detach())
print("final loss:", round(loss.item(), 4))

# RL link: this training loop = policy/value network training in RL (same opt.step)
