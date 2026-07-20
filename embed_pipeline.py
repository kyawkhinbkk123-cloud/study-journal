"""
embed_pipeline.py — morning embed orchestrator (run after computer ON).
1. test-call loop: retry test_embed.py every 60min until 200 (reset detected)
2. on 200 -> run day-48.py (524 embed, valid key, 1020 cached)
3. run test_2way.py (analysis PASS + signal REJECT + iATR)
4. print summary for iATR / recap

Usage: python embed_pipeline.py
(computer must be ON; reset ~03:45 estimate, rolling +24h)
"""
import os, sys, subprocess, time

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(SCRIPTS, "study_journal")
PY = sys.executable

def run(script, cwd=None, timeout=600):
    p = subprocess.run([PY, script], cwd=cwd or SCRIPTS,
                        capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr

def wait_for_reset(max_wait_h=12, retry_min=60):
    """Loop test_embed.py until 200 OK (quota reset)."""
    deadline = time.time() + max_wait_h * 3600
    while time.time() < deadline:
        rc, out, err = run("test_embed.py")
        print(f"[test-call] rc={rc}\n{out[-300:]}")
        if "200 OK" in out:
            print("RESET CONFIRMED — proceeding to embed")
            return True
        if "429" in out:
            print(f"  429 — wait {retry_min}min, retry")
            time.sleep(retry_min * 60)
        else:
            print(f"  unexpected: {err[-200:]}")
            time.sleep(retry_min * 60)
    print("TIMEOUT — reset not detected in window")
    return False

if __name__ == "__main__":
    print("=== EMBED PIPELINE (computer ON) ===")
    if not wait_for_reset():
        sys.exit(1)
    print("\n=== STEP 2: 524 embed (day-48) ===")
    rc, out, err = run("day-48.py", cwd=JOURNAL, timeout=1800)
    print(out[-500:])
    if rc != 0:
        print("EMBED FAILED:", err[-300:]); sys.exit(1)
    print("\n=== STEP 3: 2-way test ===")
    rc, out, err = run("test_2way.py")
    print(out[-500:])
    print("\n=== PIPELINE DONE — iATR/recap ready ===")
