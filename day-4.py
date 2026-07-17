# M1 Day 4 - Git + mini project: study tracker CLI (Feynman own build)

import json
import pathlib

# A tiny CLI that logs study sessions to JSON (own build, not copied)
LOG = pathlib.Path("study_journal/study_log.json")

def log_day(day, topic, minutes):
    data = json.loads(LOG.read_text()) if LOG.exists() else []
    data.append({"day": day, "topic": topic, "minutes": minutes})
    LOG.write_text(json.dumps(data, indent=2))
    print(f"logged day {day}: {topic} ({minutes} min)")

def show():
    if not LOG.exists():
        print("no log yet"); return
    data = json.loads(LOG.read_text())
    total = sum(d["minutes"] for d in data)
    print(f"sessions: {len(data)} | total minutes: {total}")

if __name__ == "__main__":
    log_day(4, "Git + CLI mini project", 90)
    show()
