"""
fetch_news.py — Newsdata.io -> study_inbox (kind='news').

Trading-AI / learning context: daily finance + AI news auto-fetched
into study pipeline (same path as photo/text from telegram_bot).

NOT an LLM provider — data source (like NVIDIA embed).
Free tier: 200 req/day, 1 req/min (cron 08:00 safe).

Verified: newsdata.io live returns articles (2026-07-19).
"""
import os, json, sqlite3, subprocess, time, urllib.parse

# load .env
for _cand in ["../.env", "../../.env", "C:/Users/user/AppData/Local/hermes/.env"]:
    if os.path.exists(_cand):
        for _l in open(_cand, encoding="utf-8", errors="replace"):
            _l = _l.strip()
            if _l and not _l.startswith("#") and "=" in _l:
                _k, _v = _l.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
        break

NEWS_KEY = os.environ.get("NEWSDATA_API_KEY", "").strip()
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study.db")
# categories relevant to trading-AI learning
QUERY = "gold OR forex OR XAUUSD OR AI OR machine learning"
COUNTRY = "us"
MAX_ITEMS = 5


def _fetch() -> list:
    if not NEWS_KEY:
        print("NO NEWSDATA_API_KEY")
        return []
    url = (f"https://newsdata.io/api/1/news?apikey={NEWS_KEY}"
           f"&q={urllib.parse.quote(QUERY)}&country={COUNTRY}&language=en&size={MAX_ITEMS}")
    out = subprocess.run(["curl", "-s", "--max-time", "25", url],
                         capture_output=True, text=True, timeout=30)
    try:
        r = json.loads(out.stdout)
    except Exception:
        print("parse fail:", out.stdout[:100])
        return []
    if r.get("status") != "success":
        print("API fail:", r.get("message", out.stdout[:80]))
        return []
    return r.get("results", [])


def _to_inbox(articles: list) -> int:
    conn = sqlite3.connect(DB)
    n = 0
    for a in articles:
        title = a.get("title", "").strip()
        desc = a.get("description", "").strip()
        src = a.get("source_id") or a.get("source", "")
        link = a.get("link", "")
        if not title:
            continue
        content = f"[NEWS] {title}\n{desc}\n— {src}\n{link}"
        # dedupe by link
        if link and conn.execute("SELECT 1 FROM study_inbox WHERE content LIKE ?", (f"%{link}%",)).fetchone():
            continue
        conn.execute("INSERT INTO study_inbox(kind, content, created_at, processed) VALUES(?,?,?,?)",
                     ("news", content, time.time(), 0))
        n += 1
    conn.commit()
    conn.close()
    return n


def main():
    arts = _fetch()
    if not arts:
        print("no articles fetched")
        return
    n = _to_inbox(arts)
    print(f"fetched {len(arts)} -> {n} new news items -> study_inbox(kind='news')")


if __name__ == "__main__":
    main()
