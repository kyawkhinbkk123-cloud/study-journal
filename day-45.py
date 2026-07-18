"""
M11 Day 45 — Edge LLM / Quantization (simulation, no local model).

Path 1 specialized #2. Kyaw machine = 8GB, NO local models (memory rule).
So: theory + math sim, NOT real inference.

Quantization: FP16 weights -> INT8. Sim:
  - size: 16-bit -> 8-bit = 2x smaller
  - accuracy: rounding error (simulate with deterministic noise model)
  - speed: fewer bits -> faster (theoretical)

Study claim: quantization trades a little accuracy for 2x size + speed.
Edge = run smaller model on device (no cloud). Sim shows the tradeoff.

Test: simulate 4 weights, quantize FP16->INT8, measure round-trip error.
No network -> sandbox-safe (auto-pipeline compatible).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def quantize_fp16_to_int8(values: list) -> tuple:
    """Simulate FP16->INT8 quantization + dequantization (round-trip error)."""
    # scale to int8 range [-127, 127]
    max_abs = max(abs(v) for v in values) or 1.0
    scale = 127.0 / max_abs
    q = [int(round(v * scale)) for v in values]          # int8
    deq = [x / scale for x in q]                          # dequantized
    errors = [abs(orig - dq) for orig, dq in zip(values, deq)]
    max_err = max(errors)
    avg_err = sum(errors) / len(errors)
    size_ratio = 16 / 8  # 2x smaller
    return q, deq, {"max_err": max_err, "avg_err": avg_err, "size_ratio": size_ratio}


def main():
    # simulate 4 model weights (FP16 range)
    weights = [0.81, -0.34, 0.12, -0.95]
    q, deq, stats = quantize_fp16_to_int8(weights)
    print(f"ORIG:   {weights}")
    print(f"INT8:   {q}")
    print(f"DEQUANT:{[round(x, 3) for x in deq]}")
    print(f"STATS:  {stats}")
    # assert: 2x smaller, error small (quantization loss acceptable)
    assert stats["size_ratio"] == 2.0
    assert stats["max_err"] < 0.05, f"quant error too high: {stats['max_err']}"
    assert all(-127 <= x <= 127 for x in q), "int8 overflow"
    print("PASS: quantization sim (2x smaller, round-trip error < 0.05)")


if __name__ == "__main__":
    main()
