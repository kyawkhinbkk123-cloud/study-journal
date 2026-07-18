"""
verify.py - verify-before-use layer. stdlib only.

Contract (bamboo-fence):
    scan(code)                 -> [hit, ...]        empty == clean
    path_safe(path)            -> bool
    compile_check(code)        -> (ok, err)
    run_sandbox(code, timeout) -> {"ok","stdout","stderr","reason"}
    verify_code(code)          -> {"status","detail"}   status: pass|fail|blocked

Design note: scan() runs on a NORMALISED copy of the source so that os . system
and OS.System do not slip past. Obfuscation primitives (import, getattr, eval,
exec, base64 decode) are treated as danger themselves - we refuse.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ------------------------------------------------------------- danger set
DANGER = [
    (r"\bos\.system\b",                    "os.system"),
    (r"\bos\.popen\b",                     "os.popen"),
    (r"\bos\.exec[lv]?[pe]{0,2}\b",        "os.exec*"),
    (r"\bos\.rmdir\b|\bos\.removedirs\b",  "os dir delete"),
    (r"\bshutil\.rmtree\b",                "shutil.rmtree"),
    (r"\bimport\s*\(",                 "import (obfuscation)"),
    (r"\bgetattr\s*\(",                    "getattr (obfuscation)"),
    (r"\beval\s*\(",                       "eval"),
    (r"\bexec\s*\(",                       "exec"),
    (r"\bcompile\s*\(",                    "compile"),
    (r"\bpickle\.loads?\b",                "pickle load"),
    (r"\bmarshal\.loads\b",                "marshal.loads"),
    (r"\bctypes\b",                        "ctypes"),
    (r"\bwinreg\b|\b_winreg\b",            "winreg"),
    (r"\bimport\s+socket\b|\bsocket\.socket\b", "raw socket"),
    (r"\bb64decode\b|\bbase64\.b64decode\b",    "base64 decode (obfuscation)"),
    (r"\bcodecs\.decode\s*\(",             "codecs.decode (obfuscation)"),
    (r"\bopen\s*\([^)]*['\"][rwa]?[wa]\+?['\"]", "file write"),
    (r"\bsys\.modules\b",                  "sys.modules tamper"),
    (r"\bsetattr\s*\(\s*builtins",     "builtins tamper"),
]

# -------------------------------------------------------- module guard
# study code must NEVER import local infra modules (tunnel to subprocess/curl/keys)
BLOCKED_MODULES = [
    "providers",      # tunnel to _post -> curl subprocess, leaks API keys
    "telegram_bot",   # bot control / token access
    "study",          # db write / push to inbox
    "verify",         # self-bypass
    "sync_role",      # role file overwrite
    "__audit",        # audit tamper
    "config",         # config tamper
]

# --------------------------------------------------- network allowlist (tier-2)
# danger-scan blocks DESTRUCTIVE ops (os.system/rmtree/eval). Network (curl/
# urllib) is legitimate for provider calls (embed/agent study). Allow ONLY
# known API domains. Dynamic URL build (concat/var) is unverifiable -> block.
# NOTE: static allowlist is PARTIAL (no runtime redirect / DNS rebind catch).
# Real fix = OS network restrict (proxy/firewall). Study code = self-authored,
# low threat model -> this tier is sufficient. Convention: literal API URL only.
NETWORK_ALLOWLIST = [
    "api.groq.com",
    "generativelanguage.googleapis.com",
    "integrate.api.nvidia.com",
    "api.telegram.org",
    "en.wikipedia.org",
    "api.openrouter.ai",
    "api.mistral.ai",
]


def _network_ok(code: str) -> list:
    """Allow network to allowlisted hosts only.
    Host must be LITERAL (en.wikipedia.org). Query/path vars (?q={x}) OK.
    Dynamic HOST build (f"https://{host}" or "https://"+h) = evasion -> block.
    """
    c = code.casefold()
    hits = []
    hosts = re.findall(r"https?://([a-z0-9.\-]+)", c, re.I)
    for host in hosts:
        hl = host.lower()
        allowed = any(hl == d.lower() or hl.endswith("." + d.lower())
                      for d in NETWORK_ALLOWLIST)
        if not allowed:
            hits.append(f"non-allowlist: {host}")
    # dynamic HOST build (entire host is var/concat) = evasion. query var = OK.
    if (re.search(r"https?://\{", c)
            or re.search(r"https?://.*?\+", c)
            or re.search(r"\+.*?https?://", c)):
        hits.append("dynamic host build (evasion)")
    return hits



BLOCKED_ROOTS = [
    r"c:\windows",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\programdata",
    r"/etc", r"/sys", r"/proc", r"/boot", r"/dev",
]
BLOCKED_TOKENS = ["system32", "syswow64", "\\windows\\", "/windows/"]


def _normalise(code: str) -> str:
    """Collapse evasion whitespace, unify quotes/slashes, casefold."""
    s = code.casefold()
    s = re.sub(r"\s*\.\s*", ".", s)      # os . system  -> os.system
    s = re.sub(r"\s*\(\s*", "(", s)      # eval  (      -> eval(
    s = s.replace("/", "\\") if re.search(r"[a-z]:\\", s) else s
    return s


def scan(code: str) -> list[str]:
    """Return list of danger labels found. Empty list == clean."""
    src = _normalise(code)
    hits: list[str] = []

    for pattern, label in DANGER:
        if re.search(pattern, src):
            hits.append(label)

    for mod in BLOCKED_MODULES:
        if re.search(rf"\bimport\s+{re.escape(mod)}\b|\bfrom\s+{re.escape(mod)}\s+import", src):
            hits.append(f"blocked module import: {mod}")

    if re.search(r"['\"]\s*\+\s*['\"]", src) and re.search(r"import|system|exec|eval", src):
        hits.append("string-concat evasion")

    for m in re.finditer(r"['\"]([^'\"\n]{3,260})['\"]", src):
        if not path_safe(m.group(1)):
            hits.append(f"blocked path: {m.group(1)[:60]}")

    # tier-2: network allowlist (legitimate provider calls only)
    hits += _network_ok(src)

    # static lint: pyflakes (pip, system-installed) catches undefined names
    # py_compile misses runtime NameError (e.g. y undefined in genexpr scope)
    _pyflakes_check(code, hits)

    return sorted(set(hits))


# layer-3 status (pyflakes present in this env). Audit reads this.
LINT_LAYER3_ACTIVE = None  # None=unchecked, True/False after first scan


def _pyflakes_check(code: str, hits: list[str]) -> None:
    """Undefined-name / unused detection via pyflakes.
    pyflakes is a SYSTEM dependency (pip-installed in Python310), NOT imported
    into study sandbox code — stdlib-only rule applies to study code, not tools.
    If absent -> flag LINT_LAYER3_ACTIVE=False (audit must warn, NOT silent skip)."""
    global LINT_LAYER3_ACTIVE
    try:
        import pyflakes.api, pyflakes.reporter
    except Exception:
        LINT_LAYER3_ACTIVE = False
        hits.append("WARN: pyflakes absent - layer-3 (undefined-name) OFF")
        return
    LINT_LAYER3_ACTIVE = True
    import io
    out = io.StringIO()
    reporter = pyflakes.reporter.Reporter(out, out)
    try:
        pyflakes.api.check(code, filename="<study>", reporter=reporter)
    except Exception as e:
        hits.append(f"lint error: {e}")
        return
    for line in out.getvalue().splitlines():
        if "undefined name" in line:
            name = line.rsplit("'", 2)[1] if "'" in line else "?"
            hits.append(f"undefined name: {name}")
        elif "imported but unused" in line:
            hits.append("unused import")



def path_safe(path: str) -> bool:
    """False if the path resolves into a protected system location."""
    if not path or not isinstance(path, str):
        return True
    p = path.strip().strip("'\"").casefold()
    if not re.search(r"[\\/]", p):
        return True
    p = p.replace("/", "\\")
    p = os.path.normpath(p)          # kills  ..\..\  traversal
    while "\\\\" in p:               # collapse doubled separators
        p = p.replace("\\\\", "\\")

    for root in BLOCKED_ROOTS:
        r = root.replace("/", "\\")
        if p == r or p.startswith(r + "\\"):
            return False
    return not any(tok.replace("/", "\\") in p for tok in BLOCKED_TOKENS)


def compile_check(code: str) -> tuple[bool, str]:
    """Syntax check without executing anything."""
    import ast
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"line {e.lineno}: {e.msg}"


def run_sandbox(code: str, timeout: int = 10) -> dict:
    """Run ONLY after scan() is clean. Temp cwd, no inherited env secrets."""
    hits = scan(code)
    if hits:
        return {"ok": False, "stdout": "", "stderr": "",
                "reason": "blocked: " + ", ".join(hits)}

    ok, err = compile_check(code)
    if not ok:
        return {"ok": False, "stdout": "", "stderr": err, "reason": "syntax error"}

    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "snippet.py"
        f.write_text(code, encoding="utf-8")
        # pass a safe copy of the environment (keep Windows system vars so
        # Python can initialise; strip obvious secrets)
        _SECRET = ("KEY", "TOKEN", "SECRET", "PASSWORD", "API")
        env = {k: v for k, v in os.environ.items()
                if not any(s in k.upper() for s in _SECRET)}
        env.setdefault("PYTHONIOENCODING", "utf-8")
        try:
            r = subprocess.run([sys.executable, str(f)], cwd=td, env=env,
                               capture_output=True, text=True, timeout=timeout)
            return {"ok": r.returncode == 0,
                    "stdout": r.stdout[-2000:],
                    "stderr": r.stderr[-800:],
                    "reason": "" if r.returncode == 0 else f"exit {r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "",
                    "reason": f"timeout {timeout}s"}


def verify_code(code: str, timeout: int = 10) -> dict:
    """One-shot: blocked / fail / pass."""
    hits = scan(code)
    if hits:
        return {"status": "blocked", "detail": ", ".join(hits)}
    ok, err = compile_check(code)
    if not ok:
        return {"status": "fail", "detail": err}
    r = run_sandbox(code, timeout)
    if r["ok"]:
        return {"status": "pass", "detail": r["stdout"].strip()[:600] or "(no output)"}
    return {"status": "fail", "detail": (r["reason"] + " " + r["stderr"]).strip()[:600]}
