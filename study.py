"""
study.py - Telegram learning pipeline core. Python stdlib only + providers + verify.

Contract (bamboo-fence):
    push(kind, content, image_path=None) -> id     (telegram_bot.py calls this)
    run_session()                        -> str    (cron / Task Scheduler calls this)

Flow:
    inbox has material -> per item:
        image / text -> LLM -> Burmese study note JSON
        code         -> LLM -> step-by-step explain + reusable patterns + bugs
        verify-before-use -> execute test_code in sandbox -> adopt ONLY if PASS
        save to study_notes -> deliver formatted text
    inbox empty -> 3-line recap + 1 practice, costing 0 API calls
        (recap_line/practice are written at STUDY time, not at recap time)

Own tables only (study_inbox, study_notes). memory.py schema is untouched.
"""
from __future__ import annotations

import base64
import os
import pathlib
import re
import sqlite3
import time
import urllib.parse
import urllib.request

import providers
import verify

_DIR = pathlib.Path(__file__).resolve().parent

DB = os.environ.get("STUDY_DB", "").strip() or str(_DIR / "study.db")
CHAT_ID = os.environ.get("STUDY_CHAT_ID", "8192230588").strip()
TG_TOKEN = (os.environ.get("STUDY_BOT_TOKEN")
            or os.environ.get("TELEGRAM_TOKEN", "")).strip()
MAX_ITEMS_PER_RUN = int(os.environ.get("STUDY_MAX_ITEMS", "3"))
SANDBOX_TIMEOUT = int(os.environ.get("STUDY_SANDBOX_TIMEOUT", "12"))

CODE_EXT = {".py", ".mq5", ".mqh", ".pine", ".js", ".ts", ".c", ".cpp", ".java"}

_ICON = {"pass": "✅ PASS", "fail": "❌ FAIL",
         "blocked": "⛔ BLOCKED", "reasoned": "🧠 REASONED"}


# ----------------------------------------------------------------------- db
def _db() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS study_inbox(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT,
        content TEXT,
        image_path TEXT,
        created_at REAL,
        processed INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS study_notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT,
        topic TEXT,
        note TEXT,
        lesson TEXT,
        recap_line TEXT,
        practice TEXT,
        verify_status TEXT,
        verify_detail TEXT,
        provider TEXT,
        created_at REAL);
    CREATE TABLE IF NOT EXISTS study_meta(
        key TEXT PRIMARY KEY,
        val TEXT);
    """)
    return c


def _get_meta(key: str, default: str = "") -> str:
    c = _db()
    r = c.execute("SELECT val FROM study_meta WHERE key=?", (key,)).fetchone()
    c.close()
    return r[0] if r else default


def _set_meta(key: str, val: str) -> None:
    c = _db()
    c.execute("INSERT OR REPLACE INTO study_meta(key,val) VALUES(?,?)", (key, val))
    c.commit()
    c.close()


def classify(text: str, image_path: str | None = None) -> str:
    """image | code | text"""
    if image_path:
        return "image"
    t = text or ""

    # strong hint: telegram_bot prepends "# file: name.ext" for uploaded files
    m = re.search(r"^#\s*file:\s*\S+(\.\w+)\s*$", t, re.M)
    if m and m.group(1).lower() in CODE_EXT:
        return "code"

    code_marks = len(re.findall(
        r"^\s*(def |class |import |from .+ import|#include|void |"
        r"return |print\(|if __name__|async def|try:|except |@\w+|"
        r"//\+\+\+|OnTick|OnInit|function |const |let |public )", t, re.M))
    braces = t.count("{") + t.count("}") + t.count(";")
    if code_marks >= 2 or (braces >= 6 and "\n" in t):
        return "code"
    return "text"


def push(kind: str, content: str, image_path: str | None = None) -> int:
    """Queue material. kind: auto | image | code | text"""
    if kind == "auto":
        kind = classify(content, image_path)
    with _db() as c:
        cur = c.execute(
            "INSERT INTO study_inbox(kind,content,image_path,created_at) "
            "VALUES(?,?,?,?)",
            (kind, content or "", image_path or "", time.time()))
        return int(cur.lastrowid)


# ------------------------------------------------------------------ prompts
SYS = (
    "You are Hermes, Kyaw's study agent. Reason in English internally, "
    "OUTPUT Burmese only (technical terms may stay English). "
    "Be short and exact - လိုတိုရှင်း. No filler, no praise, no repetition. "
    "Never invent facts; if unsure, say so. "
    "HARD RULE: an LLM opinion is never a live trading signal. "
    "STRUCTURE RULE: always use these ENGLISH labels for the field names "
    "(values may be Burmese): **Topic:**  **Note:**  **Lesson:**  "
    "**Recap line:**  **Practice:**  **Test code:**"
)


_JSON_TAIL = (
    'Return ONLY a JSON object, no markdown fence, with keys:\n'
    '{"topic": str, "note": [str], "lesson": str, "recap_line": str, '
    '"practice": str, "test_code": str}\n'
    '- note: max 5 bullets, Burmese, one line each.\n'
    '- note: max 5 bullets, Burmese, one line each.\n'
    '- lesson: 1 durable reusable insight (Burmese).\n'
    '- recap_line: ONE Burmese line for later recall.\n'
    '- practice: ONE concrete exercise Kyaw can do (Burmese).\n'
    '- test_code: self-contained python3 stdlib-only snippet PROVING the core '
    'claim, printing PASS or FAIL. No file writes, no network, no subprocess, '
    'no eval/exec, no pip. Empty string "" if the claim cannot be executed.'
)


def _ask(user_msg: str, image_b64: str | None = None,
         mime: str = "image/jpeg") -> dict:
    return providers.chat_json(
        [{"role": "user", "content": user_msg}],
        system=SYS, image_b64=image_b64, image_mime=mime,
        max_tokens=1400, temperature=0.2,
    )


def study_image(path: str) -> dict:
    p = pathlib.Path(path)
    b64 = base64.b64encode(p.read_bytes()).decode()
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    msg = ("ဒီ infographic/article ပုံကို လေ့လာပြီး study note ထုတ်ပါ။ "
           "အဓိက claim တစ်ခုကို ရွေးပြီး test_code နဲ့ သက်သေပြပါ။\n\n" + _JSON_TAIL)
    return _ask(msg, image_b64=b64, mime=mime)


def study_text(text: str) -> dict:
    msg = ("အောက်က article/concept ကို လေ့လာပြီး study note ထုတ်ပါ။ "
           "အဓိက claim တစ်ခုကို test_code နဲ့ သက်သေပြပါ။\n\n"
           f"---\n{text[:12000]}\n---\n\n" + _JSON_TAIL)
    return _ask(msg)


def study_code(src: str) -> dict:
    msg = ("အောက်က code (Claude AI ရေးတာ ဖြစ်နိုင်) ကို အစအဆုံး ဖတ်ပါ။ "
           "ဘာလုပ်တာလဲ အဆင့်လိုက် ရှင်းပါ။ reusable pattern ထုတ်ပါ။ "
           "bug ရှိရင် ထောက်ပြပါ။\n\n"
           f"---\n{src[:14000]}\n---\n\n"
           "note bullets ထဲမှာ step-by-step + bug/improvement ပါစေ။\n" + _JSON_TAIL)
    return _ask(msg)


# ------------------------------------------------------------------- verify
def _looks_python(src: str) -> bool:
    """MQL5 / Pine must never reach the python sandbox."""
    if re.search(r"OnTick|OnInit|#property|//\+\+\+|input\s+\w+\s*=", src):
        return False
    if "//@version" in src or "indicator(" in src or "strategy(" in src:
        return False
    return compile_ok(src)


def compile_ok(src: str) -> bool:
    return verify.compile_check(src)[0]


def _verify(item_kind: str, src: str, res: dict) -> dict:
    """Never trust the model's claim - execute it."""
    if item_kind == "code" and _looks_python(src):
        v = verify.verify_code(src, timeout=SANDBOX_TIMEOUT)
        if v["status"] != "blocked":
            return v
        # blocked -> cannot run Kyaw's code safely; fall back to model's snippet

    tc = (res.get("test_code") or "").strip()
    if not tc:
        return {"status": "reasoned",
                "detail": "execute မလုပ်နိုင် — reasoning သာ (adopt မလုပ်ရသေး)"}
    return verify.verify_code(tc, timeout=SANDBOX_TIMEOUT)


# -------------------------------------------------------------------- store
def _save(kind: str, res: dict, v: dict) -> int:
    with _db() as c:
        cur = c.execute(
            "INSERT INTO study_notes(kind,topic,note,lesson,recap_line,practice,"
            "verify_status,verify_detail,provider,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (kind,
             str(res.get("topic", ""))[:200],
             "\n".join(res.get("note") or []),
             str(res.get("lesson", "")),
             str(res.get("recap_line", ""))[:300],
             str(res.get("practice", "")),
             v["status"],
             v["detail"][:800],
             str(res.get("_provider", "?")),
             time.time()))
        return int(cur.lastrowid)


# ------------------------------------------------------------------ deliver
def deliver(text: str) -> bool:
    """Telegram sendMessage. No token -> print (test mode)."""
    if not TG_TOKEN:
        print(text)
        return False
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    ok = True
    chunks = [text[i:i + 3800] for i in range(0, len(text), 3800)] or [""]
    for chunk in chunks:
        data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": chunk}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30)
        except Exception as e:
            print(f"[deliver] {type(e).__name__}: {e}")
            ok = False
    return ok


def _format(kind: str, res: dict, v: dict) -> str:
    bullets = "\n".join(f"• {b}" for b in (res.get("note") or [])[:5])
    adopt = "adopt ✅" if v["status"] == "pass" else "adopt မလုပ်ရသေး ⏸"
    return (f"📘 {res.get('topic', '(topic မရှိ)')}  [{kind}]\n"
            f"{bullets}\n\n"
            f"🔎 Verify: {_ICON.get(v['status'], v['status'])} — {v['detail'][:300]}\n"
            f"→ {adopt}\n\n"
            f"💡 Lesson: {res.get('lesson', '-')}\n"
            f"🏋 Practice: {res.get('practice', '-')}\n"
            f"({res.get('_provider', '?')})")


# -------------------------------------------------------------------- recap
def recap() -> str:
    """0 API calls: reads pre-written recap_line rows."""
    with _db() as c:
        rows = c.execute(
            "SELECT recap_line, practice, verify_status, topic FROM study_notes "
            "ORDER BY id DESC LIMIT 3").fetchall()
    if not rows:
        return ("🔁 Recap: သင်ခန်းစာ မှတ်တမ်း မရှိသေးပါ။\n"
                "🏋 Practice: infographic ဒါမှမဟုတ် code တစ်ခု ပို့ပြီး pipeline စစ်ပါ။")
    lines = [f"{i}. {line or topic} [{_ICON.get(vs, vs)}]"
             for i, (line, _p, vs, topic) in enumerate(rows, 1)]
    return ("🔁 Recap (material အသစ် မရောက်သေး):\n" + "\n".join(lines) +
            f"\n\n🏋 Practice: {rows[0][1] or '-'}")


# --------------------------------------------------------------- entrypoint
def run_session() -> str:
    today = time.strftime("%Y-%m-%d")
    last_run = _get_meta("last_run", "")
    catchup_note = ""
    if last_run and last_run < today:
        gap = (time.mktime(time.strptime(today, "%Y-%m-%d")) -
               time.mktime(time.strptime(last_run, "%Y-%m-%d"))) / 86400
        catchup_note = (f"🔄 Catch-up: last run {last_run}, {int(gap)} day(s) gap "
                        f"(computer was off). Resuming from pending inbox + next day.\n")
    _set_meta("last_run", today)

    with _db() as c:
        items = c.execute(
            "SELECT id, kind, content, image_path FROM study_inbox "
            "WHERE processed=0 ORDER BY id LIMIT ?",
            (MAX_ITEMS_PER_RUN,)).fetchall()

    if not items:
        out = recap()
        if catchup_note:
            out = catchup_note + out
        deliver(out)
        return out

    if catchup_note:
        deliver(catchup_note)
    sent = []
    for _id, kind, content, img in items:
        try:
            if kind == "image":
                res = study_image(img)
            elif kind == "code":
                res = study_code(content)
            else:
                res = study_text(content)
            v = _verify(kind, content, res)
            _save(kind, res, v)
            msg = _format(kind, res, v)
        except providers.ProviderError as e:
            msg = (f"⚠️ provider အားလုံး မရ — {e}\n"
                   f"(item {_id} ကို မဖျက်ဘူး၊ နောက် run မှာ ပြန်ကြိုးစားမယ်)")
            deliver(msg)
            return msg  # leave unprocessed, do not burn keys further
        except Exception as e:
            msg = f"⚠️ item {_id} ({kind}) မအောင်မြင် — {type(e).__name__}: {e}"

        with _db() as c:
            c.execute("UPDATE study_inbox SET processed=1 WHERE id=?", (_id,))
        deliver(msg)
        sent.append(msg)

    return "\n\n".join(sent)


if __name__ == "__main__":
    print(run_session())
