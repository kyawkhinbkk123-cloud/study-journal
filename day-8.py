# M3 Day 8 - PyTorch tensors (Feynman own build)

import torch

# Tensor = NumPy array with GPU support + autograd (for DL/RL gradients)
x = torch.tensor([1.0, 2.0, 3.0])
y = torch.tensor([2.0, 4.0, 6.0])
print("x:", x, "y:", y)
print("x*y:", x * y)

# A "neural" weight we will learn (autograd tracks math)
w = torch.tensor([1.0], requires_grad=True)
pred = w * x
loss = ((pred - y) ** 2).mean()
loss.backward()
print("loss:", round(loss.item(), 3), "grad w:", round(w.grad.item(), 3))

# RL link: gradient descent updates policy/value weights = same backward() idea
print("device:", "cuda" if torch.cuda.is_available() else "cpu")
