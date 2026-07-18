"""
M9 Day 38 — Agent error recovery via state checkpoint.

Day 32 gap: overnight cron crashed mid-run -> no resume point, re-ran from
start, wasted quota. Fix: persist progress to study.db (day_status table)
after EACH day completes. On restart, skip done, resume in-progress, retry failed.

Pattern = Hermes cron resilience (provider_state cooldown is the same idea:
don't repeat work that already succeeded).

Study claim: resilient agent = checkpoint-after-each-step + idempotent resume.
Test: simulate 5 days, crash after day 3, restart -> resumes at 4, skips 1-3.
"""
import sys, os, sqlite3, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "study.db")


def _connect():
    return sqlite3.connect(DB)


def init_checkpoint():
    c = _connect()
    c.execute("""CREATE TABLE IF NOT EXISTS day_status (
        day INTEGER PRIMARY KEY,
        status TEXT,            -- done | in_progress | failed
        note_id INTEGER,
        ts REAL
    )""")
    c.commit(); c.close()


def mark(day: int, status: str, note_id=None):
    c = _connect()
    c.execute("INSERT OR REPLACE INTO day_status(day,status,note_id,ts) "
              "VALUES(?,?,?,?)", (day, status, note_id, time.time()))
    c.commit(); c.close()


def get_status(day: int) -> str:
    c = _connect()
    r = c.execute("SELECT status FROM day_status WHERE day=?", (day,)).fetchone()
    c.close()
    return r[0] if r else "pending"


def pending_days(total: int) -> list:
    """Resume point: skip done, return pending/in_progress/failed."""
    return [d for d in range(1, total + 1) if get_status(d) != "done"]


def run_day(day: int, crash_after=None) -> int:
    """Simulate a study day. Returns note_id (fake). Crash if day==crash_after.
    If already in_progress from prior crash, retry (idempotent)."""
    if get_status(day) == "done":
        return 1000 + day
    mark(day, "in_progress")
    if crash_after and day == crash_after:
        raise RuntimeError(f"crash at day {day}")
    note_id = 1000 + day  # fake note
    mark(day, "done", note_id)
    return note_id


def main():
    init_checkpoint()
    TOTAL = 5
    # --- run 1: days 1-3, crash at 3 ---
    print("=== RUN 1 (crash at day 3) ===")
    for d in pending_days(TOTAL):
        try:
            run_day(d, crash_after=3)
            print(f"  day {d}: done")
        except RuntimeError as e:
            print(f"  day {d}: CRASH ({e})")
            break
    print(f"  status d1-3: {[get_status(d) for d in range(1,4)]}")

    # --- run 2: resume, should retry 3 (in_progress), do 4-5 ---
    print("=== RUN 2 (resume) ===")
    todo = pending_days(TOTAL)
    print(f"  resume at: {todo}")
    assert todo == [3, 4, 5], f"should retry 3 + do 4-5, got {todo}"
    for d in todo:
        # no crash this time -> day 3 retries and completes
        run_day(d)
        print(f"  day {d}: done")
    print(f"  all done: {[get_status(d) for d in range(1,TOTAL+1)]}")
    assert all(get_status(d) == "done" for d in range(1, TOTAL + 1))
    print("PASS: checkpoint + idempotent resume (crash at 3 -> resumed 4-5)")


if __name__ == "__main__":
    main()
