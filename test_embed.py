"""
test_embed.py — 1-chunk gemini-embed-2 reset-confirm (morning, before 524 batch).
Run after quota reset (~03:45). Prints 200 (OK) or 429 (wait).
"""
import os, sys, json, urllib.request, urllib.error

# load .env (last-wins valid key)
seen = {}
for cand in ["../.env", "../../.env", "C:/Users/user/AppData/Local/hermes/.env"]:
    if os.path.exists(cand):
        for l in open(cand, encoding="utf-8", errors="replace"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1)
                seen[k.strip()] = v.strip()
        break
os.environ.update(seen)

KEY = os.environ.get("GEMINI_API_KEY", "")
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2-preview:embedContent?key=" + KEY

TEST_CHUNK = "double sl = iATR(NULL,0,14,0); int ticket = OrderSend(Symbol(),OP_BUY,Lots,Ask,3,Ask-sl*Point,Ask+tp*Point,\"EA\",0,0,Green);"

def embed(text):
    payload = json.dumps({"content": {"parts": [{"text": text}]}}).encode()
    req = urllib.request.Request(URL, data=payload, headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=30)

if __name__ == "__main__":
    if not KEY:
        print("FAIL: no GEMINI_API_KEY")
        sys.exit(1)
    try:
        r = embed(TEST_CHUNK)
        d = json.loads(r.read())
        emb = d.get("embedding", {}).get("values", [])
        print(f"200 OK — dim={len(emb)}, first3={[round(x,3) for x in emb[:3]]}")
        print("RESET CONFIRMED: run 524 embed now")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("429 — quota NOT reset yet, wait + retry")
        else:
            print(f"HTTP {e.code}: {e.read()[:120]}")
    except Exception as e:
        print(f"ERR: {e}")
