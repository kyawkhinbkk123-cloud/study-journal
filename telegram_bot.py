"""
telegram_bot.py - getUpdates poller. Python stdlib ONLY (urllib). No SDK, no pip.

⚠️ TWO COLLISIONS - read before copying this file:
   1. NAME: the existing agent already has a telegram_bot.py. Copying this over it
      DESTROYS that file. Back it up first.
   2. TOKEN: this reads TELEGRAM_TOKEN (per spec Rule 5) - the SAME var the old bot
      uses. Polling one token from two processes returns HTTP 409 Conflict and kills
      both. So: stop the old bot, OR put a second bot's token in TELEGRAM_TOKEN.
      _lock() below catches the same-machine case; 409 handling catches the rest.

Rules honoured: (1) from __future__ import annotations (2) __file__ (3) 4-space
(4) photo bytes via write_bytes(r.read()) - never .decode(), never the JSON helper
(5) keys from os.environ only (6) getFile -> largest photo -> push("auto",caption,path)
(7) text -> push("auto", text, None)  (8) poll() raises RuntimeError with no token.

Split for testability (test_bot_safe.py):
    handle_update(update, photo_dl=, doc_dl=) -> id | None   pure, no network
    download_photo(file_id)                   -> path        network, mocked in tests
    poll()                                    -> loop        calls the two above
"""
from __future__ import annotations

import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

import providers
import study

# load real .env from HERMES_ROOT so TELEGRAM_TOKEN etc are available
HERMES_ROOT = pathlib.Path(__file__).resolve().parent.parent
_env_path = HERMES_ROOT / ".env"
if _env_path.exists():
    for _line in _env_path.read_text("utf-8", "replace").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        os.environ.setdefault(_k, _v)

_DIR = pathlib.Path(__file__).resolve().parent

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_CHAT = os.environ.get("STUDY_CHAT_ID", "8192230588").strip()
MEDIA_DIR = pathlib.Path(os.environ.get("STUDY_MEDIA_DIR", "").strip()
                         or str(_DIR / "media"))
OFFSET_FILE = _DIR / "tg_offset.txt"
LOCK_FILE = _DIR / "tg_poll.lock"
POLL_TIMEOUT = 50

TEXT_EXT = {".py", ".txt", ".md", ".mq5", ".mqh", ".json", ".pine", ".csv", ".log"}
MAX_DOC_BYTES = 512 * 1024


def _api(method: str, params: dict | None = None) -> dict:
    """Telegram JSON API. Never used for file bytes - see _download_binary()."""
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode(params or {}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data),
                                timeout=POLL_TIMEOUT + 15) as r:
        out = json.loads(r.read().decode("utf-8"))
    if not out.get("ok"):
        raise RuntimeError(f"{method}: {out.get('description')}")
    return out["result"]


def _download_binary(file_id: str, suffix: str) -> str:
    """
    getFile (JSON) -> file_path -> download RAW BINARY -> local path. NETWORK.

    Rule 4: the bytes are written with dest.write_bytes(r.read()). A JPEG starts
    with 0xff 0xd8 - .decode()/read_text() would raise UnicodeDecodeError or
    silently corrupt it. _api() is used ONLY for the getFile JSON, never the bytes.
    """
    info = _api("getFile", {"file_id": file_id})
    src = f"https://api.telegram.org/file/bot{TOKEN}/{info['file_path']}"
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    dest = MEDIA_DIR / f"{int(time.time() * 1000)}{suffix}"

    req = urllib.request.Request(src)
    with urllib.request.urlopen(req, timeout=40) as r:
        dest.write_bytes(r.read())     # raw binary. NEVER .decode()
    return str(dest)


def download_photo(file_id: str) -> str:
    return _download_binary(file_id, ".jpg")


def download_document(file_id: str, name: str) -> str:
    return _download_binary(file_id, pathlib.Path(name).suffix or ".bin")


# ------------------------------------------------------------------- routing
def handle_update(update: dict, photo_dl=None, doc_dl=None) -> int | None:
    """
    Pure routing. Returns study_inbox id, or None if ignored.
    photo_dl / doc_dl are injected so tests can run with no network.
    """
    photo_dl = photo_dl or download_photo
    doc_dl = doc_dl or download_document

    msg = update.get("message") or update.get("channel_post") or {}
    if not msg:
        return None

    chat_id = str(msg.get("chat", {}).get("id", ""))
    if ALLOWED_CHAT and chat_id != ALLOWED_CHAT:
        return None  # ignore everyone else

    text = (msg.get("text") or msg.get("caption") or "").strip()

    # commands
    if text.startswith("/"):
        cmd = text.split()[0].lower().lstrip("/").split("@")[0]
        if cmd == "run":
            study.deliver(study.run_session())
        elif cmd == "recap":
            study.deliver(study.recap())
        elif cmd == "providers":
            rows = providers.status()
            study.deliver("\n".join(
                f"{r['name']:11} key={'✅' if r['key'] else '—'} "
                f"{r['calls_today']}/{r['cap']} cool={r['cooldown_s']}s"
                for r in rows))
        else:
            study.deliver("commands: /run /recap /providers")
        return None

    image_path = None
    if msg.get("photo"):
        best = max(msg["photo"], key=lambda p: p.get("file_size", 0))
        image_path = photo_dl(best["file_id"])

    if msg.get("document"):
        doc = msg["document"]
        name = doc.get("file_name", "file.bin")
        ext = pathlib.Path(name).suffix.lower()
        if ext in TEXT_EXT and doc.get("file_size", 0) <= MAX_DOC_BYTES:
            path = doc_dl(doc["file_id"], name)
            body = pathlib.Path(path).read_text("utf-8", errors="replace")
            text = f"{text}\n\n# file: {name}\n{body}".strip()
        elif ext in {".jpg", ".jpeg", ".png", ".webp"}:
            image_path = doc_dl(doc["file_id"], name)

    if not text and not image_path:
        return None
    return study.push("auto", text, image_path)


# ---------------------------------------------------------------------- loop
def _offset(new: int | None = None) -> int:
    if new is not None:
        OFFSET_FILE.write_text(str(new), encoding="utf-8")
        return new
    try:
        return int(OFFSET_FILE.read_text("utf-8").strip())
    except Exception:
        return 0


def _lock() -> bool:
    """Single-instance guard: a second poller on this machine refuses to start."""
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        try:
            owner = LOCK_FILE.read_text("utf-8").strip()
        except Exception:
            owner = "?"
        print(f"[study_bot] lock held by pid {owner}. If that process is dead, "
              f"delete {LOCK_FILE} and retry.")
        return False


def poll() -> None:
    # Rule 8: refuse to poll without a token. Raised HERE, not at import time,
    # so tests can import this module with no token set.
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set - refusing to poll")
    if not _lock():
        return

    print(f"[study_bot] polling. chat={ALLOWED_CHAT or 'ANY'} media={MEDIA_DIR}")
    try:
        while True:
            try:
                ups = _api("getUpdates",
                           {"offset": _offset(), "timeout": POLL_TIMEOUT})
            except urllib.error.HTTPError as e:
                if e.code == 409:
                    print("[study_bot] HTTP 409 Conflict - another process is "
                          "polling this same TELEGRAM_TOKEN. Stopping.")
                    return
                print(f"[study_bot] HTTP {e.code}; retry in 10s")
                time.sleep(10)
                continue
            except Exception as e:
                print(f"[study_bot] {type(e).__name__}: {e}; retry in 10s")
                time.sleep(10)
                continue

            for up in ups:
                _offset(up["update_id"] + 1)
                try:
                    new_id = handle_update(up)
                    if new_id:
                        # AUTO-NOTE: process the new item immediately with Gemini
                        # (vision) and deliver the study note — no /run needed.
                        study.deliver(f"📥 inbox #{new_id} — လေ့လာနေသည်… ⏳")
                        try:
                            study.run_session()
                        except Exception as e:
                            study.deliver(f"⚠️ auto-note error: {type(e).__name__}: {e}")
                except Exception as e:
                    print(f"[study_bot] update {up.get('update_id')}: "
                          f"{type(e).__name__}: {e}")
    finally:
        LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    poll()
