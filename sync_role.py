# sync_role.py - Keep MAIN_ROLE.md in sync across all load points.
# Run after editing scripts/MAIN_ROLE.md.
# Off-system (file copy only) - no approval needed.
import os, shutil, hashlib, sys

HERMES = "C:/Users/user/AppData/Local/hermes"
SRC = os.path.join(HERMES, "scripts", "MAIN_ROLE.md")
DST_SOUL = os.path.join(HERMES, "SOUL.md")
DST_JOURNAL = os.path.join(HERMES, "scripts", "study_journal", "MAIN_ROLE.md")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def main():
    if not os.path.exists(SRC):
        print("ERROR: source missing", SRC)
        sys.exit(1)
    src_hash = sha(SRC)
    changes = []
    for dst in (DST_SOUL, DST_JOURNAL):
        if sha(dst) != src_hash:
            shutil.copy2(SRC, dst)
            changes.append(dst)
    if changes:
        print("SYNCED ->")
        for c in changes:
            print("  ", c)
    else:
        print("ALREADY IN SYNC (no copy needed)")
    # report drift status
    print(f"hash MAIN_ROLE={src_hash[:10]}")
    print(f"hash SOUL     ={sha(DST_SOUL)[:10]} {'OK' if sha(DST_SOUL)==src_hash else 'DRIFT'}")
    print(f"hash JOURNAL  ={sha(DST_JOURNAL)[:10]} {'OK' if sha(DST_JOURNAL)==src_hash else 'DRIFT'}")


if __name__ == "__main__":
    main()
