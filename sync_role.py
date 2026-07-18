# sync_role.py - Keep all 4 architecture files in sync across load points.
# Run after editing any of: MAIN_ROLE.md, MEMORY_MAP.md, MEMORY_LESSONS.md, PITFALLS.md
# in scripts/. Copies them to study_journal/ (git). MAIN_ROLE.md ALSO copies to SOUL.md.
# Off-system (file copy only) - no approval needed.
import os, shutil, hashlib, sys

HERMES = "C:/Users/user/AppData/Local/hermes"
SCRIPTS = os.path.join(HERMES, "scripts")
JOURNAL = os.path.join(SCRIPTS, "study_journal")
SOUL = os.path.join(HERMES, "SOUL.md")

# (source in scripts/, also copy to SOUL.md?)
FILES = [
    ("STUDY_ROLE.md", True),     # -> SOUL.md + journal
    ("MEMORY_MAP.md", False),
    ("MEMORY_LESSONS.md", False),
    ("PITFALLS.md", False),
]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def main():
    changes = []
    for fname, to_soul in FILES:
        src = os.path.join(SCRIPTS, fname)
        if not os.path.exists(src):
            print(f"⚠️  missing {src}")
            continue
        src_h = sha(src)
        # journal copy
        dst_j = os.path.join(JOURNAL, fname)
        if sha(dst_j) != src_h:
            shutil.copy2(src, dst_j)
            changes.append(f"journal/{fname}")
        # SOUL copy (MAIN_ROLE only)
        if to_soul:
            if sha(SOUL) != src_h:
                shutil.copy2(src, SOUL)
                changes.append("SOUL.md")
    if changes:
        print("SYNCED ->")
        for c in changes:
            print("   ", c)
    else:
        print("ALREADY IN SYNC (no copy needed)")
    # drift report for all 4
    for fname, to_soul in FILES:
        src = os.path.join(SCRIPTS, fname)
        src_h = sha(src)
        j = sha(os.path.join(JOURNAL, fname))
        s = sha(SOUL) if to_soul else "n/a"
        jok = "OK" if j == src_h else "DRIFT"
        sok = "" if not to_soul else f" soul={'OK' if s==src_h else 'DRIFT'}"
        print(f"  {fname:22} journal={jok}{sok}")


if __name__ == "__main__":
    main()
