#!/usr/bin/env python3
import csv
import os
import re
from datetime import datetime
from pathlib import Path

BASE = Path("experiments/k3s/node-failure")

def read_time(path):
    if not path.exists():
        return None
    return datetime.fromisoformat(path.read_text().strip())

def parse_requests(path):
    total = success = failed = 0
    first_failure = last_failure = first_success_after_failure = None

    if not path.exists():
        return None

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            ts = datetime.fromisoformat(row["timestamp"])
            ok = row["success"].strip().lower() == "true"

            if ok:
                success += 1
                if last_failure and first_success_after_failure is None:
                    first_success_after_failure = ts
            else:
                failed += 1
                if first_failure is None:
                    first_failure = ts
                last_failure = ts
                first_success_after_failure = None

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "success_rate": round(success / total * 100, 2) if total else 0,
        "error_rate": round(failed / total * 100, 2) if total else 0,
        "first_failure": first_failure,
        "last_failure": last_failure,
        "first_success_after_failure": first_success_after_failure,
    }

def count_restarts(pods_file):
    if not pods_file.exists():
        return None
    text = pods_file.read_text()
    restarts = []
    for line in text.splitlines():
        if line.startswith("nginx-test"):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    restarts.append(int(parts[3]))
                except ValueError:
                    pass
    return sum(restarts) if restarts else 0

def event_contains(events_file, pattern):
    if not events_file.exists():
        return False
    return re.search(pattern, events_file.read_text(), re.IGNORECASE) is not None

print("run,type,total,success,failed,success_rate,error_rate,recovery_seconds,pod_restarts_after,node_notready,node_ready,manual_recovery")

for run in sorted(BASE.iterdir()):
    if not run.is_dir():
        continue

    name = run.name
    if "worker" in name:
        typ = "worker"
    elif "server" in name:
        typ = "server"
    else:
        typ = "unknown"

    req = parse_requests(run / "requests.csv")
    if req is None:
        continue

    fault = read_time(run / "fault_time.txt")
    recovery = read_time(run / "recovery_time_observed.txt")

    recovery_seconds = ""
    if fault and recovery:
        recovery_seconds = round((recovery - fault).total_seconds(), 1)

    restarts_after = count_restarts(run / "pods_after.txt")

    events_all = ""
    for fname in ["events_during.txt", "events_after.txt"]:
        p = run / fname
        if p.exists():
            events_all += p.read_text() + "\n"

    node_notready = "NodeNotReady" in events_all
    node_ready = "NodeReady" in events_all

    notes = (run / "notes.txt").read_text() if (run / "notes.txt").exists() else ""
    manual_recovery = "systemctl restart k3s" in notes or "manuell" in notes.lower()

    print(
        f"{name},{typ},{req['total']},{req['success']},{req['failed']},"
        f"{req['success_rate']},{req['error_rate']},{recovery_seconds},"
        f"{restarts_after},{node_notready},{node_ready},{manual_recovery}"
    )
