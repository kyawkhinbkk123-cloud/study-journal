# M3 Day 10 - CNN basics (Feynman own build: tiny conv on dummy image)

import torch
import torch.nn as nn

# A 1-channel 8x8 "image", 2 fake classes
X = torch.randn(4, 1, 8, 8)   # batch=4, ch=1, 8x8
y = torch.tensor([0, 1, 0, 1])

model = nn.Sequential(
    nn.Conv2d(1, 4, kernel_size=3),  # conv: local features
    nn.ReLU(),
    nn.MaxPool2d(2),                 # downsample
    nn.Flatten(),
    nn.Linear(4 * 3 * 3, 2),         # 8-3+1=6 -> pool 3x3 -> 2 classes
)
opt = torch.optim.Adam(model.parameters(), lr=0.01)
loss_fn = nn.CrossEntropyLoss()

for ep in range(150):
    opt.zero_grad()
    out = model(X)
    loss = loss_fn(out, y)
    loss.backward()
    opt.step()

print("logits:\n", out.detach().round())
print("final loss:", round(loss.item(), 4))

# RL link: CNN feature extractor can be the "eyes" of a vision-agent (state from pixels)
