"""
providers.py - FREE LLM provider rotation. stdlib only (urllib), no SDK.

Contract (bamboo-fence):
    chat(messages, system=..., json_mode=..., image_b64=...) -> {"text":str, "provider":str}
    chat_json(...)                                           -> dict (parsed)

Rules enforced here:
  - nous is primary, 6 free fallbacks after it.
  - one key is never exhausted: per-provider DAILY CAP + cooldown on 429/401.
  - state persists to provider_state.json so scheduled runs remember dead keys.

NOTE: base_url / model defaults may drift. Override any of them in .env
      (e.g. NOUS_BASE_URL=..., GROQ_MODEL=...) without touching this file.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request

_DIR = pathlib.Path(__file__).resolve().parent
_DIR = pathlib.Path(__file__).resolve().parent

# load real .env from HERMES_ROOT so API keys are available (Claude version
# reads os.environ only; this loader makes .env work for scheduled/cron runs)
HERMES_ROOT = _DIR.parent
_STATE_FILE = _DIR / "provider_state.json"
_env_path = HERMES_ROOT / ".env"
if _env_path.exists():
    for _line in _env_path.read_text("utf-8", "replace").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        os.environ.setdefault(_k, _v)

TIMEOUT = int(os.environ.get("PROVIDER_TIMEOUT", "90"))
DAILY_CAP = int(os.environ.get("PROVIDER_DAILY_CAP", "150"))

COOLDOWN_RATE_LIMIT = 15 * 60      # 429
COOLDOWN_BAD_KEY = 24 * 60 * 60    # 401 / 403
COOLDOWN_SERVER = 5 * 60           # 5xx / network


class ProviderError(RuntimeError):
    pass


# ---------------------------------------------------------------- registry
# order == priority. nous first, then 6 free fallbacks.
PROVIDERS = [
    {
        "name": "nous",
        "kind": "openai",
        "base": ("NOUS_BASE_URL", "https://inference-api.nousresearch.com/v1"),
        "model": ("NOUS_MODEL", "Hermes-4-405B"),
        "key": "NOUS_API_KEY",
        "vision": False,
    },
    {
        "name": "gemini",
        "kind": "gemini",
        "base": ("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
        "model": ("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        "key": "GEMINI_API_KEY",
        "vision": True,
    },
    {
        "name": "groq",
        "kind": "openai",
        "base": ("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        "model": ("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "key": "GROQ_API_KEY",
        "vision": False,
    },
    {
        "name": "cerebras",
        "kind": "openai",
        "base": ("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
        "model": ("CEREBRAS_MODEL", "llama-3.3-70b"),
        "key": "CEREBRAS_API_KEY",
        "vision": False,
    },
    {
        "name": "openrouter",
        "kind": "openai",
        "base": ("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "model": ("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        "key": "OPENROUTER_API_KEY",
        "vision": True,
    },
    {
        "name": "mistral",
        "kind": "openai",
        "base": ("MISTRAL_BASE_URL", "https://api.mistral.ai/v1"),
        "model": ("MISTRAL_MODEL", "mistral-small-latest"),
        "key": "MISTRAL_API_KEY",
        "vision": False,
    },
    {
        "name": "deepseek",
        "kind": "openai",
        "base": ("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "model": ("DEEPSEEK_MODEL", "deepseek-chat"),
        "key": "DEEPSEEK_API_KEY",
        "vision": False,
    },
]


# ------------------------------------------------------------------ state
def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _load_state() -> dict:
    try:
        return json.loads(_STATE_FILE.read_text("utf-8"))
    except Exception:
        return {}


def _save_state(st: dict) -> None:
    try:
        _STATE_FILE.write_text(json.dumps(st, indent=1), encoding="utf-8")
    except Exception:
        pass  # state is an optimisation, never fatal


def _slot(st: dict, name: str) -> dict:
    s = st.setdefault(name, {})
    if s.get("day") != _today():
        s["day"] = _today()
        s["calls"] = 0
    s.setdefault("calls", 0)
    s.setdefault("cooldown_until", 0)
    s.setdefault("fails", 0)
    return s


def _cool(st: dict, name: str, seconds: int, why: str) -> None:
    s = _slot(st, name)
    s["cooldown_until"] = time.time() + seconds
    s["fails"] = s.get("fails", 0) + 1
    s["last_error"] = why
    _save_state(st)
def status() -> list[dict]:
    """Human-readable view. Used by /providers command and self-check."""
    st = _load_state()
    out = []
    for p in PROVIDERS:
        s = _slot(st, p["name"])
        left = max(0, int(s["cooldown_until"] - time.time()))
        out.append({
            "name": p["name"],
            "key": bool(os.environ.get(p["key"], "").strip()),
            "calls_today": s["calls"],
            "cap": DAILY_CAP,
            "cooldown_s": left,
            "last_error": s.get("last_error", ""),
        })
    return out


# ------------------------------------------------------------------- http
def _post(url: str, payload: dict, headers: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


# --------------------------------------------------------- payload shapes
def _openai_payload(p, messages, system, json_mode, image_b64, image_mime,
                    max_tokens, temperature) -> dict:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    for m in messages:
        msgs.append(dict(m))
    if image_b64:
        last = msgs[-1]
        last["content"] = [
            {"type": "text", "text": last.get("content", "")},
            {"type": "image_url",
             "image_url": {"url": f"data:{image_mime};base64,{image_b64}"}},
        ]
    payload = {
        "model": os.environ.get(p["model"][0], p["model"][1]),
        "messages": msgs,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return payload


def _gemini_payload(messages, system, json_mode, image_b64, image_mime,
                    max_tokens, temperature) -> dict:
    contents = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
    if image_b64:
        contents[-1]["parts"].append(
            {"inline_data": {"mime_type": image_mime, "data": image_b64}})
    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    return payload


def _gemini_text(data: dict) -> str:
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(x.get("text", "") for x in parts)


# ------------------------------------------------------------------- main
def chat(messages, *, system=None, json_mode=False, image_b64=None,
         image_mime="image/png", max_tokens=1200, temperature=0.3,
         prefer=None) -> dict:
    """Try providers in priority order. Returns {"text", "provider"}."""
    st = _load_state()
    errors = []

    order = list(PROVIDERS)
    if prefer:
        order.sort(key=lambda p: 0 if p["name"] == prefer else 1)

    for p in order:
        name = p["name"]
        key = os.environ.get(p["key"], "").strip()
        s = _slot(st, name)

        if not key:
            errors.append(f"{name}: no key")
            continue
        if image_b64 and not p["vision"]:
            errors.append(f"{name}: no vision")
            continue
        # RESERVE gemini for IMAGES ONLY — save its free quota for vision.
        # Text goes to mistral/openrouter/groq etc. (unless gemini explicitly preferred)
        if not image_b64 and name == "gemini" and prefer != "gemini":
            errors.append("gemini: reserved for vision")
            continue
        if s["cooldown_until"] > time.time():
            errors.append(f"{name}: cooldown {int(s['cooldown_until']-time.time())}s")
            continue
        if s["calls"] >= DAILY_CAP:
            errors.append(f"{name}: daily cap {DAILY_CAP}")
            continue

        base = os.environ.get(p["base"][0], p["base"][1]).rstrip("/")
        model = os.environ.get(p["model"][0], p["model"][1])
        try:
            if p["kind"] == "gemini":
                url = f"{base}/models/{model}:generateContent?key={key}"
                payload = _gemini_payload(messages, system, json_mode, image_b64,
                                          image_mime, max_tokens, temperature)
                data = _post(url, payload, {})
                text = _gemini_text(data)
            else:
                url = f"{base}/chat/completions"
                payload = _openai_payload(p, messages, system, json_mode, image_b64,
                                          image_mime, max_tokens, temperature)
                data = _post(url, payload, {"Authorization": f"Bearer {key}"})
                if not isinstance(data, dict) or "choices" not in data:
                    raise RuntimeError(f"bad/empty response from {name}: {str(data)[:160]}")
                text = data["choices"][0]["message"]["content"]

            s["calls"] += 1
            s["fails"] = 0
            s["last_error"] = ""
            _save_state(st)
            return {"text": (text or "").strip(), "provider": name}

        except urllib.error.HTTPError as e:
            code = e.code
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            if code == 429:
                retry = e.headers.get("Retry-After")
                wait = int(retry) if (retry or "").isdigit() else COOLDOWN_RATE_LIMIT
                _cool(st, name, wait, f"429 {detail}")
            elif code in (401, 403):
                _cool(st, name, COOLDOWN_BAD_KEY, f"{code} bad key")
            else:
                _cool(st, name, COOLDOWN_SERVER, f"{code} {detail}")
            errors.append(f"{name}: HTTP {code}")

        except Exception as e:  # URLError, timeout, malformed body
            _cool(st, name, COOLDOWN_SERVER, repr(e)[:120])
            errors.append(f"{name}: {type(e).__name__}")

    raise ProviderError("all providers unavailable -> " + " | ".join(errors))


def chat_json(messages, **kw) -> dict:
    """chat() + tolerant JSON parse (strips code fence)."""
    kw.setdefault("json_mode", True)
    res = chat(messages, **kw)
    raw = res["text"].strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip().removeprefix("json").strip()
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        i, j = raw.find("{"), raw.rfind("}")
        if i != -1 and j > i:
            try:
                out = json.loads(raw[i:j + 1])
            except json.JSONDecodeError:
                out = None
        else:
            out = None
    # fallback: model returned markdown (**Topic:** / **Note:** / bullets) not JSON
    if not isinstance(out, dict):
        out = _parse_markdown_note(raw)
    if not isinstance(out, dict):
        raise ProviderError(f"not JSON from {res['provider']}: {raw[:120]}")
    out["_provider"] = res["provider"]
    return out


def _parse_markdown_note(text: str) -> dict:
    """Best-effort parse of a markdown study note into the JSON shape.

    Accepts forms like:
        **Topic:** foo
        **Note:**
        * a
        * b
        **Lesson:** ...
    Returns {} if it cannot find at least a Topic.
    """
    out: dict = {}
    cur = None
    note_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # skip model-added image captions / noise
        if line.startswith("[Caption:") or line.startswith("**[Caption:"):
            continue
        # match **Topic:** / **Note:** / **ခေါင်းစဉ်:** etc — colon may sit
        # INSIDE or OUTSIDE the ** bold. Both forms appear from real models.
        m = re.match(r"\*\*\s*([A-Za-z\u1000-\u109f\s]+?)\s*:?\s*\*\*\s*:?\s*(.*)", line, re.I)
        if m:
            label = m.group(1).lower().replace(" ", "_").replace("-", "_")
            val = m.group(2).strip()
            # map EN + Burmese labels -> schema keys
            _MAP = {
                "topic": "topic", "ခေါင်းစဉ်": "topic", "ခေါင်းစဉ်": "topic",
                "note": "note", "မှတ်စု": "note",
                "lesson": "lesson", "သင်ခန်းစာ": "lesson",
                "recap_line": "recap_line", "ပြန်ခေါ်မေ": "recap_line", "recap": "recap_line",
                "practice": "practice", "လေ့ကျင့်": "practice",
                "test_code": "test_code", "စမ်းသပ်ကုဒ်": "test_code",
            }
            key = _MAP.get(label, label)
            if key == "note":
                cur = "note"
                if val:
                    note_lines.append(val)
            elif key == "recap_line":
                out["recap_line"] = val
            elif key == "test_code":
                out["test_code"] = val
            else:
                out[key] = val
                cur = key
        elif cur == "note" and line.startswith("*"):
            note_lines.append(line.lstrip("*").strip())
        elif cur == "note":
            note_lines.append(line)
    if not out.get("topic"):
        # last-resort: model returned freeform prose (no **Topic:** label).
        # Synthesize a note from a title + bullet/bold lines so we never
        # drop a valid vision/text answer as "topic မရှိ".
        title = ""
        bullets: list[str] = []
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("[Caption:"):
                continue
            if not title:
                # prefer a quoted "Title" or a **bold** heading, else first line
                qm = re.search(r'"([^"]{3,80})"', s)
                bm = re.match(r"\*+\s*(.+?)\s*\*+\s*$", s)
                if qm:
                    title = qm.group(1)
                elif bm:
                    title = re.sub(r"\*+", "", bm.group(1)).strip()
                elif len(s) > 8:
                    title = re.sub(r"\*+", "", s)[:80]
            # collect bullet / bold-lead lines as note points
            b = s.lstrip("*-•").strip()
            b = re.sub(r"\*\*(.+?)\*\*", r"\1", b)
            if b and b != title and len(b) > 3:
                bullets.append(b[:160])
        if title:
            return {
                "topic": title[:200],
                "note": bullets[:6],
                "lesson": "",
                "recap_line": title[:120],
                "practice": "",
                "test_code": "",
            }
        return {}
    if note_lines:
        out["note"] = note_lines
    out.setdefault("note", [])
    out.setdefault("lesson", "")
    out.setdefault("recap_line", "")
    out.setdefault("practice", "")
    out.setdefault("test_code", "")
    return out


if __name__ == "__main__":
    for row in status():
        print(f"{row['name']:11} key={str(row['key']):5} "
              f"{row['calls_today']}/{row['cap']} cool={row['cooldown_s']}s "
              f"{row['last_error']}")
