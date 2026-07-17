# M7 Day 26 - LLM caching + rate limiting (Feynman own build)
# Production essential: cache repeat prompts (save cost/quota), rate-limit calls.

import sys, time, hashlib, sqlite3, pathlib
sys.path.insert(0, ".")
import providers

# --- CACHE: store prompt->response in SQLite (avoid re-calling LLM) ---
CACHE_DB = "study_journal/llm_cache.db"
def _init():
    c = sqlite3.connect(CACHE_DB)
    c.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT, ts REAL)")
    c.commit(); c.close()

def cached_chat(prompt, ttl=3600):
    key = hashlib.sha256(prompt.encode()).hexdigest()
    c = sqlite3.connect(CACHE_DB)
    row = c.execute("SELECT v, ts FROM cache WHERE k=?", (key,)).fetchone()
    if row and (time.time() - row[1]) < ttl:
        c.close()
        return row[0], "CACHE_HIT"
    resp = providers.chat([{"role": "user", "content": prompt}])
    text = resp["text"] if isinstance(resp, dict) else str(resp)
    c.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, text, time.time()))
    c.commit(); c.close()
    return text, "LLM_CALL"

# --- RATE LIMITER: token-bucket, max N calls per window ---
class RateLimiter:
    def __init__(self, max_calls, window):
        self.max_calls, self.window = max_calls, window
        self.calls = []
    def allow(self):
        now = time.time()
        self.calls = [t for t in self.calls if now - t < self.window]
        if len(self.calls) < self.max_calls:
            self.calls.append(now); return True
        return False

if __name__ == "__main__":
    _init()
    p = "What is 2+2? Answer with one number."
    # first call -> LLM, second -> cache
    r1, src1 = cached_chat(p); print(f"call 1: {r1.strip()[:20]} [{src1}]")
    r2, src2 = cached_chat(p); print(f"call 2: {r2.strip()[:20]} [{src2}]")
    assert src2 == "CACHE_HIT", "cache failed"
    # rate limiter test
    rl = RateLimiter(max_calls=3, window=10)
    allowed = [rl.allow() for _ in range(5)]
    print("rate limiter (3/10s), 5 requests:", allowed)
    assert allowed == [True, True, True, False, False], "rate limit failed"
    print("PASS: cache + rate limiter both work")
