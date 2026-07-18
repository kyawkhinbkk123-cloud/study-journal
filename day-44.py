"""
M11 Day 44 — Multimodal RAG (TRUE multimodal, Gemini Embedding 2).

Path 1 specialized #1. M8 built text RAG (nvidia 2048). M11 adds images
via TRUE multimodal embedding: gemini-embedding-2-preview projects BOTH
text and image into the SAME 3072-dim space. No caption projection.

Verified 07-19: text embed dim=3072, image embed dim=3072 (shared space).
Free tier 1500 req/day. GEMINI_API_KEY.

Study claim: true multimodal RAG = one embedder for all modalities,
standard cosine retrieval. Image nuance preserved (not lost in caption).

Test: 2 text chunks + 1 image chunk. Query about image topic ->
image chunk should rank top in shared space.
"""
import sys, os, json, subprocess, tempfile, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env")
if not os.path.exists(_env):
    _env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(_env):
    for _l in open(_env, encoding="utf-8", errors="replace"):
        _l = _l.strip()
        if _l and not _l.startswith("#") and "=" in _l:
            _k, _v = _l.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def _gem_embed(text: str = None, image_b64: str = None) -> list:
    """True multimodal embed (text and/or image -> 3072-dim shared space)."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-embedding-2-preview:embedContent?key={key}")
    parts = []
    if text:
        parts.append({"text": text})
    if image_b64:
        parts.append({"inline_data": {"mime_type": "image/png", "data": image_b64}})
    payload = json.dumps({"content": {"parts": parts}})
    cfg = tempfile.NamedTemporaryFile(mode="w", suffix=".curl", delete=False)
    os.chmod(cfg.name, 0o600)
    cfg.write('header = "Content-Type: application/json"\n')
    cfg.write(f'url = "{url}"\n')
    cfg.close()
    cmd = ["curl", "-s", "--max-time", "30", "-X", "POST", "-K", cfg.name, "-d", payload]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    finally:
        try:
            os.remove(cfg.name)
        except OSError:
            pass
    d = json.loads(out.stdout)
    if "embedding" not in d:
        raise RuntimeError(f"embed fail: {out.stdout[:120]}")
    return d["embedding"].get("values") or d["embedding"].get("value") or []


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _minimal_png() -> str:
    """2x2 red PNG (stdlib only) for image-chunk test."""
    import zlib, struct
    w = h = 2
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * w for _ in range(h))
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw)
    return base64.b64encode(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")).decode()


def main():
    img_b64 = _minimal_png()
    # chunks: 2 text + 1 image (red square)
    chunks = {
        "t1": "Alice works at Acme in New York",
        "t2": "The weather today is sunny",
        "img_red": img_b64,  # image chunk
    }
    vecs = {}
    for k, v in chunks.items():
        if k.startswith("img_"):
            vecs[k] = _gem_embed(image_b64=v)
        else:
            vecs[k] = _gem_embed(text=v)

    # query about image (red color)
    qv = _gem_embed(text="red color square image")
    ranked = sorted(((cosine(qv, vecs[k]), k) for k in vecs), reverse=True)
    print("RANKED:", ranked)
    top = ranked[0][1]
    assert top == "img_red", f"image chunk should rank top, got {top}"
    print("PASS: true multimodal RAG (image ranks top for image query, shared 3072-dim)")


if __name__ == "__main__":
    main()
