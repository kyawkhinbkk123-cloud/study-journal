"""
__audit.py - Daily Agent Self-Audit (VERIFIED WORKING version, 2026-07-17).

Run:  python __audit.py            # live-test every key
       python __audit.py --offline   # 0 API calls, state only

Prints a structured Burmese report (5 sections). Scheduler delivers stdout verbatim.

Key facts (live-verified):
  - Gemini (vision):  ✅ OK
  - Mistral / Groq (text): ✅ OK
  - NVIDIA embed:         ✅ OK (dim=2048, curl-only — urllib 500)
  - OpenRouter:          ⚠️ 429 late-day (free 150/day)
  - urllib git-bash → SSL 1010 → OpenAI tests use curl subprocess
  - bot-alive: reads tg_poll.lock pid, scans ps
  - cron list: hermes-agent/venv/Scripts/hermes.exe cron list
"""
import os, json, pathlib, time, subprocess, sqlite3, urllib.request, urllib.error, sys

DIR = pathlib.Path(__file__).resolve().parent
PY = r"C:/Users/user/AppData/Local/Programs/Python/Python310/python.exe"
HERMES = r"C:/Users/user/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe"
OFFLINE = "--offline" in sys.argv

import sys
if str(DIR) not in sys.path:
    sys.path.insert(0, str(DIR))


def env_get(k):
    for l in pathlib.Path(r"C:\Users\user\AppData\Local\hermes\.env").read_text("utf-8", "replace").splitlines():
        if l.startswith(k + "="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def http_post(url, headers, body_dict, timeout=25):
    data = json.dumps(body_dict).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode(), 0
    except urllib.error.HTTPError as e:
        return e.read().decode(), e.code
    except Exception as e:
        return json.dumps({"error": str(e)}), 1


def test_gemini(key):
    if not key:
        return "❌ key မရှိ"
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-3.1-flash-lite-preview:generateContent?key={key}")
    body = {"contents": [{"parts": [{"text": "hi"}]}]}
    raw, _ = http_post(url, {"Content-Type": "application/json"}, body)
    try:
        d = json.loads(raw)
        return "✅ OK (vision)" if "candidates" in d else "❌ " + d.get("error", {}).get("message", raw[:60])
    except Exception:
        return "❌ bad resp " + raw[:50]


def test_openai(base, key, model):
    if not key:
        return "❌ key မရှိ"
    url = base.rstrip("/") + "/chat/completions"
    body = {"model": model, "messages": [{"role": "user", "content": "hi"}],
             "max_tokens": 1}
    # curl (urllib git-bash SSL 1010)
    out = subprocess.run(
        ["curl", "-s", "--max-time", "25", "-X", "POST", url,
         "-H", f"Authorization: Bearer {key}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(body)],
        capture_output=True, text=True, timeout=35)
    try:
        d = json.loads(out.stdout)
        if "choices" in d:
            return "✅ OK"
        code = d.get("error", {}).get("code")
        if code == 429:
            return "⚠️ 429 rate-limit (free tier used up)"
        if code in (401, 403):
            return "❌ key invalid/expired"
        return "❌ " + d.get("error", {}).get("message", out.stdout[:50])
    except Exception:
        return "❌ bad resp " + out.stdout[:40]


def test_nvidia(key):
    if not key:
        return "❌ key မရှိ"
    body = {"input": "test", "model": "nvidia/nemotron-3-embed-1b",
            "input_type": "query"}
    # curl (urllib 500 — gateway strips Authorization)
    out = subprocess.run(
        ["curl", "-s", "--max-time", "25", "-X", "POST",
         "https://integrate.api.nvidia.com/v1/embeddings",
         "-H", f"Authorization: Bearer {key}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(body)],
        capture_output=True, text=True, timeout=35)
    try:
        d = json.loads(out.stdout)
        return f"✅ OK (dim={len(d['data'][0]['embedding'])})" if "data" in d else "❌ " + d.get("error", {}).get("message", out.stdout[:50])
    except Exception:
        return "❌ bad resp " + out.stdout[:40]


def bot_alive():
    lock = DIR / "tg_poll.lock"
    pid = None
    if lock.exists():
        try:
            pid = lock.read_text().strip()
        except Exception:
            pid = None
    if pid:
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-Process -Id {pid} -ErrorAction SilentlyContinue "
                 f"| Select-Object ProcessId,CommandLine | Format-List"],
                capture_output=True, text=True, timeout=15)
            if "telegram_bot" in out.stdout:
                return f"✅ alive (pid {pid})"
        except Exception:
            pass
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"name='python.exe'\""
             " | Select-Object ProcessId,CommandLine | Format-List"],
            capture_output=True, text=True, timeout=15)
        for line in out.stdout.splitlines():
            if "telegram_bot" in line:
                return "✅ alive (pid in ps)"
    except Exception:
        pass
    return "⚠️ bot process not found"


def cron_state():
    try:
        out = subprocess.run([HERMES, "cron", "list"],
                            capture_output=True, text=True, timeout=20)
        txt = out.stdout + out.stderr
        n = txt.count("Name:")
        return f"cron jobs: {n}"
    except Exception as e:
        return f"cron err: {e}"


def note_quality():
    db = DIR / "study.db"
    if not db.exists():
        return "⚠️ study.db မရှိ"
    c = sqlite3.connect(str(db))
    total = c.execute("SELECT COUNT(*) FROM study_notes").fetchone()[0]
    bad = c.execute(
        "SELECT COUNT(*) FROM study_notes WHERE topic='' OR topic IS NULL "
        "OR verify_status='reasoned'").fetchone()[0]
    return f"notes: {total} (garbage/reasoned: {bad})"


def sync_check():
    import hashlib
    files = [
        ("MAIN_ROLE.md", True),
        ("MEMORY_MAP.md", False),
        ("MEMORY_LESSONS.md", False),
        ("PITFALLS.md", False),
    ]
    def h(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest() if p.exists() else None
    drift = []
    for fname, to_soul in files:
        src = DIR / fname
        src_h = h(src)
        if src_h is None:
            drift.append(f"{fname} မရှိ")
            continue
        if h(DIR / "study_journal" / fname) != src_h:
            drift.append(f"journal/{fname}")
        if to_soul and h(pathlib.Path(r"C:\Users\user\AppData\Local\hermes\SOUL.md")) != src_h:
            drift.append("SOUL.md")
    if drift:
        return f"❌ DRIFT: {', '.join(drift)} (run sync_role.py)"
    return "✅ all role files in sync (4 files)"


def main():
    print("🔍 DAILY AGENT SELF-AUDIT —", time.strftime("%Y-%m-%d %H:%M"))
    print()
    print("【 API KEYS — LIVE TEST 】" if not OFFLINE else "【 API KEYS — OFFLINE (state only) 】")
    keys = {
        "Gemini (vision)": ("GEMINI_API_KEY", lambda k: test_gemini(k)),
        "OpenRouter (text)": ("OPENROUTER_API_KEY",
            lambda k: test_openai("https://openrouter.ai/api/v1", k, "meta-llama/llama-3.3-70b-instruct:free")),
        "Mistral (text)": ("MISTRAL_API_KEY",
            lambda k: test_openai("https://api.mistral.ai/v1", k, "mistral-small-latest")),
        "Groq (text)": ("GROQ_API_KEY",
            lambda k: test_openai("https://api.groq.com/openai/v1", k, "llama-3.3-70b-versatile")),
        "NVIDIA (embed)": ("NVIDIA_API_KEY", lambda k: test_nvidia(k)),
    }
    for label, (envk, fn) in keys.items():
        k = env_get(envk) if not OFFLINE else None
        status = fn(k) if k else "❌ key မရှိ (.env)"
        print(f"  {label:20} {status}")
    print()
    print("【 SYSTEM 】")
    print(f"  Study bot:     {bot_alive()}")
    print(f"  Notes:        {note_quality()}")
    print(f"  Cron:         {cron_state()}")
    print(f"  Role sync:    {sync_check()}")
    print()
    print("【 LLM IMPROVEMENT 】")
    try:
        st = json.loads((DIR / "provider_state.json").read_text("utf-8"))
        for name in ["gemini", "openrouter", "mistral", "groq", "nvidia"]:
            s = st.get(name, {})
            cd = s.get("cooldown_until", 0) and "YES" or "no"
            print(f"  {name:12} calls={s.get('calls',0)}/"
                  f"{s.get('cap',150)} cool={cd} err={s.get('last_error','-')[:30]}")
    except Exception as e:
        print(f"  provider_state read err: {e}")


if __name__ == "__main__":
    main()
