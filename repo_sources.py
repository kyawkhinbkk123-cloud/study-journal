"""
repo_sources.py — code_study.py အတွက် source-count guard။

blind spot: README-only repo → code file ၁ ခုမှ မ ဆွဲမိ → note ကျဉ်း (shallow),
ဒါပေမဲ့ _is_garbage (binary) က မ ဖမ်း — "shallow but well-formed"။

ဒီ helper က ၂ ခု လုပ်တယ်:
  1. select_sources() — README တစ်ခုတည်း အစား code file ကို ဦးစားပေး ဆွဲ
                        (doc ၁ + code ၂-၃ → principle နက်)
  2. repo_tier()      — rich / ok / shallow tier ပြန် (audit + note quality အတွက်)

stdlib only. code_study.py ကို minimal wiring နဲ့ ချိတ်လို့ရ (အောက် WIRING ကြည့်)။

═══════════════════════════════════════════════════════════════
WIRING — code_study.py line 61-74 (list_sources) ပြီးနောက်:

    from repo_sources import select_sources, repo_tier

    files = list_sources(repo)              # ရှိပြီးသား (max 14)
    picked = select_sources(files)          # ← ထည့်: code ဦးစားပေး ရွေး
    tier   = repo_tier(files)               # ← ထည့်: rich/ok/shallow

  ... study_repo (133-175) note dict ထဲ tier ထည့်:
    note["tier"] = tier                     # ← "quality: ok" ဘေးမှာ
    note["source_count"] = len([f for f in picked if is_code(f)])

  shallow ဆို retry ဒါမှမဟုတ် skip (မင်း policy ပေါ်မူတည်):
    if tier == "shallow":
        note["note"] = "⚠️ shallow (code source<2) — " + note["note"]
═══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

# code source extension — principle ဆွဲထုတ်ဖို့ တန်ဖိုးရှိတာ
CODE_EXT = (".py", ".ts", ".js", ".tsx", ".jsx", ".java", ".go", ".rs",
           ".cs", ".cpp", ".cc", ".c", ".h", ".hpp", ".rb", ".php",
           ".kt", ".swift", ".scala", ".vue", ".mq5", ".mqh", ".pine")
DOC_EXT = (".md", ".rst", ".txt", ".adoc")

# config file — code မဟုတ်ပေမဲ့ principle (lint/standard) ပါနိုင် (#5 angular လို)
CONFIG_HINT = ("eslint", "tsconfig", ".editorconfig", "pyproject",
               "ruff", "prettier", ".pylintrc", "setup.cfg")

MAX_PICK = 4  # note context မ ကြီးလွန်းအောင် — code 3 + doc 1


def is_code(path: str) -> bool:
    return path.lower().endswith(CODE_EXT)


def is_doc(path: str) -> bool:
    return path.lower().endswith(DOC_EXT)


def is_config(path: str) -> bool:
    p = path.lower()
    return any(h in p for h in CONFIG_HINT)


def repo_tier(files: list[str]) -> str:
    """rich (code>=2) / ok (code==1 သို့ config) / shallow (code==0)."""
    code_n = sum(1 for f in files if is_code(f))
    if code_n >= 2:
        return "rich"
    if code_n == 1 or any(is_config(f) for f in files):
        return "ok"
    return "shallow"


def select_sources(files: list[str], max_pick: int = MAX_PICK) -> list[str]:
    """
    README-only ရှောင်ဖို့ code ဦးစားပေး ရွေး။
    priority: code > config > doc။ doc ၁ ခုပဲ ထား (context ချုံ့)။
    files = list_sources() ရဲ့ output (already capped 14)။
    """
    code = [f for f in files if is_code(f)]
    config = [f for f in files if is_config(f) and f not in code]
    docs = [f for f in files if is_doc(f)]

    picked: list[str] = []
    # code အရင် (root-shallow ဦးစားပေး — path တို = entry-point ဖြစ်နိုင်)
    for f in sorted(code, key=lambda p: (p.count("/"), len(p)))[:3]:
        picked.append(f)
    # config တစ်ခု (lint/standard principle)
    if config and len(picked) < max_pick:
        picked.append(sorted(config, key=len)[0])
    # doc တစ်ခု (README ဦးစားပေး) — context အတွက်
    if docs and len(picked) < max_pick:
        readme = [d for d in docs if "readme" in d.lower()]
        picked.append(readme[0] if readme else sorted(docs, key=len)[0])
    # code သုည (shallow) ဆို — ရှိသမျှ doc ဆွဲ (note အလွတ်မဖြစ်အောင်)
    if not code:
        for d in sorted(docs, key=lambda p: (p.count("/"), len(p))):
            if d not in picked and len(picked) < max_pick:
                picked.append(d)
    return picked


if __name__ == "__main__":
    # self-test — ည run repo pattern
    tests = [
        ("README-only", ["README.md"], "shallow", 1),
        ("README+code", ["README.md", "src/app.ts"], "ok", 2),
        ("rich", ["README.md", "src/V.cs", "src/H.cs", "t/T.cs"], "rich", 4),
        ("angular config", ["README.md", ".eslintrc.json", "tsconfig.json"], "ok", 2),
        ("code-only", ["main.py", "util.py", "core.py"], "rich", 3),
    ]
    ok = True
    print(f"{'case':16} {'tier':8} {'picked':>6}  files")
    print("-" * 60)
    for name, files, exp_tier, exp_n in tests:
        tier = repo_tier(files)
        picked = select_sources(files)
        mark = "OK" if (tier == exp_tier and len(picked) == exp_n) else "FAIL"
        if mark == "FAIL":
            ok = False
        print(f"{name:16} {tier:8} {len(picked):>6}  {picked}  {mark}")
    print("-" * 60)
    print("ALL PASS" if ok else "SOME FAILED")
