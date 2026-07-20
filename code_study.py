"""code_study.py - coding / clean-code / architecture learning study.

Fetches coding learning repos via GitHub API (GITHUB_TOKEN in .env), extracts
REAL code patterns (functions/classes/decorators/structure), asks the LLM to
critique + extract reusable code-writing principles in Burmese, and saves to
code_notes.json. SOP: detailed, verified, anti-garbage.

Free-only: providers.chat() rotation; respects 429 cooldown.
"""
from __future__ import annotations
import base64
import json
import os
import pathlib
import re
import time
import urllib.request
import urllib.parse
from collections import Counter

_DIR = pathlib.Path(__file__).resolve().parent
HERMES_ROOT = _DIR.parent
_env = HERMES_ROOT / ".env"
if _env.exists():
    for line in _env.read_text("utf-8", "replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import providers
from repo_sources import select_sources, repo_tier, is_code

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"} if TOKEN else {}
NOTES_FILE = _DIR / "code_notes.json"

SYS = (
    "You are Hermes, Kyaw's study agent. OUTPUT Burmese only. Be short and exact.\n"
    "Given REAL source code, extract REUSABLE code-writing principles.\n"
    "RULES:\n"
    "1. QUOTE actual code (function signatures, decorators, class structure, "
    "naming, error handling). Do NOT describe generically.\n"
    "2. Extract PRINCIPLES: separation of concerns, naming, testing, error "
    "handling, DRY, single-responsibility. Quote the code line that proves it.\n"
    "3. If truncated, write 'UNKNOWN - truncated'. NEVER guess or echo prompt.\n"
    "4. HARD RULE: study ONLY - never a live coding instruction to execute blindly.\n"
    "Use ENGLISH labels: **Topic:** **Pattern:** **Principles:** "
    "**Example code:** **Lesson:** **Verdict:**"
)
SYS_RETRY = SYS + "\n\nCRITICAL: previous answer was garbage. Quote REAL code or write UNKNOWN. Do NOT echo."


def _get(url: str) -> dict:
    # W3 network guard: only api.github.com allowed (2-tier host-literal)
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    if host != "api.github.com":
        raise PermissionError(f"blocked host: {host} (only api.github.com)")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def list_sources(repo: str, path: str = "") -> list[str]:
    url = f"{GITHUB_API}/repos/{repo}/contents/{urllib.parse.quote(path)}" if path else f"{GITHUB_API}/repos/{repo}/contents"
    try:
        items = _get(url)
    except Exception as e:
        print(f"[!] list {repo}/{path}: {e}")
        return []
    out = []
    for it in items:
        if it["type"] == "dir" and len(out) < 14:
            out += list_sources(repo, it["path"])
        elif it["name"].endswith((".py", ".js", ".ts", ".go", ".java", ".cs", ".rs", ".md")) and len(out) < 14:
            out.append(it["path"])
    return out[:14]


def read_file(repo: str, path: str) -> str:
    try:
        data = _get(f"{GITHUB_API}/repos/{repo}/contents/{urllib.parse.quote(path)}")
        return base64.b64decode(data["content"]).decode("utf-8", "replace")
    except Exception as e:
        return f"[read error {e}]"


def extract_pattern(code: str, fname: str) -> str:
    """Pull structural lines that reveal code-writing style."""
    hits = []
    is_doc = fname.endswith(".md")
    for ln in code.splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.match(r"\s*(def|class|function|func|interface|struct|public|private|protected)\b", s, re.I):
            hits.append(s)
        elif re.search(r"@\w+|decorator|# region|try:|except|raise|\.test\(|describe\(", s, re.I):
            hits.append(s)
        elif is_doc and re.match(r"#{1,4}\s|\*\s|\d+\.\s", s):
            hits.append(s)
    uniq = []
    for h in hits:
        if h not in uniq:
            uniq.append(h)
    return "\n".join(uniq[:150])


def _is_garbage(text: str) -> bool:
    if not text or len(text) < 80:
        return True
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return True
    if len(set(lines)) / len(lines) < 0.5:
        return True
    chunks = [text[i:i+40] for i in range(0, len(text)-40, 40)]
    if chunks and Counter(chunks).most_common(1)[0][1] >= 3:
        return True
    return False


def load_notes() -> dict:
    try:
        return json.loads(NOTES_FILE.read_text("utf-8"))
    except Exception:
        return {}


def save_note(repo: str, note: dict) -> None:
    data = load_notes()
    data[repo] = note
    NOTES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def study_repo(repo: str) -> None:
    print(f"\n{'='*60}\n📦 REPO: {repo}\n{'='*60}")
    files = list_sources(repo)
    if not files:
        print("  (no source files)")
        return
    tier = repo_tier(files)
    picked = select_sources(files)
    print(f"  files: {len(files)} | tier: {tier} | picked: {len(picked)}")
    parts = []
    for f in picked:
        code = read_file(repo, f)
        logic = extract_pattern(code, f)
        if logic:
            parts.append(f"# FILE: {f}\n{logic[:2500]}")
    blob = "\n\n".join(parts)
    if not blob.strip():
        print("  (no pattern extracted)")
        return
    last_err = None
    for attempt in range(3):
        sys_p = SYS if attempt == 0 else SYS_RETRY
        try:
            res = providers.chat([{"role": "user", "content": blob}],
                                 system=sys_p, max_tokens=1200,
                                 temperature=0.15 + attempt*0.15)
            text = res["text"]
            if _is_garbage(text):
                print(f"  [!] attempt {attempt+1}: garbage, retry")
                last_err = "garbage"
                continue
            if tier == "shallow":
                text = "⚠️ shallow (code source<2) — " + text
            print(text)
            print(f"\n(provider: {res['provider']})")
            save_note(repo, {"note": text, "provider": res["provider"],
                             "quality": "ok", "tier": tier,
                             "source_count": len([f for f in picked if is_code(f)]),
                             "files": files[:6],
                             "ts": time.strftime("%Y-%m-%d %H:%M")})
            return
        except providers.ProviderError as e:
            last_err = str(e)
            print(f"  [!] LLM err: {e}")
            time.sleep(3)
    save_note(repo, {"note": "", "provider": "none", "quality": "garbage",
                     "tier": tier,
                     "error": last_err, "files": files[:6],
                     "ts": time.strftime("%Y-%m-%d %H:%M")})
    print(f"  [x] FAILED ({last_err}) -> flagged garbage")


def main() -> None:
    repos = [
        "kavaan/awesome-clean-code-projects-across-languages-and-framework",
        "SebastienDegodez/copilot-instructions",
        "iammukeshm/CleanArchitecture.WebApi",
        "excellalabs/js-best-practices-workshopper",
        "lubkoKuzenko/angular-clean-code",
        "henki-robotics/henki_ros2_best_practices",
    ]
    repos = repos[: int(os.environ.get("CODE_MAX", "4"))]
    for i, repo in enumerate(repos):
        study_repo(repo)
        if i < len(repos) - 1:
            time.sleep(8)


if __name__ == "__main__":
    main()
