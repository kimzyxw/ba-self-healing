#!/usr/bin/env python3
import csv
from pathlib import Path
from datetime import datetime, timezone
import statistics as stats

SCENARIO = Path("experiments/k3s/latency-tests/latency-1s")
THRESHOLD_RECOVERED_MS = 500.0

def parse_time(s):
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))

def read_time(path):
    return parse_time(Path(path).read_text().strip())

def read_requests(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0] == "timestamp":
                continue
            try:
                rows.append({
                    "ts": parse_time(row[0]),
                    "status": row[1],
                    "ms": float(row[2]) if row[2] else None,
                    "success": row[3] == "True",
                    "error": row[4] if len(row) > 4 else "",
                })
            except Exception:
                pass
    return rows

def summarize(rows):
    total = len(rows)
    ok = sum(1 for r in rows if r["success"])
    fail = total - ok
    lat = [r["ms"] for r in rows if r["ms"] is not None]
    return {
        "total": total,
        "ok": ok,
        "fail": fail,
        "success_rate": ok / total * 100 if total else 0,
        "error_rate": fail / total * 100 if total else 0,
        "avg_ms": stats.mean(lat) if lat else None,
        "min_ms": min(lat) if lat else None,
        "max_ms": max(lat) if lat else None,
        "median_ms": stats.median(lat) if lat else None,
    }

print("run,total,success_rate,error_rate,baseline_avg_ms,fault_avg_ms,after_avg_ms,fault_max_ms,recovery_latency_s")

for run_dir in sorted(SCENARIO.glob("run-*-router")):
    fault_time = read_time(run_dir / "fault_time.txt")
    recovery_time = read_time(run_dir / "recovery_time.txt")
    requests = read_requests(run_dir / "requests.csv")

    baseline = [r for r in requests if r["ts"] < fault_time]
    fault = [r for r in requests if fault_time <= r["ts"] < recovery_time]
    after = [r for r in requests if r["ts"] >= recovery_time]

    s_all = summarize(requests)
    s_base = summarize(baseline)
    s_fault = summarize(fault)
    s_after = summarize(after)

    recovered = None
    for r in after:
        if r["success"] and r["ms"] is not None and r["ms"] < THRESHOLD_RECOVERED_MS:
            recovered = (r["ts"] - recovery_time).total_seconds()
            break

    print(
        f"{run_dir.name},"
        f"{s_all['total']},"
        f"{s_all['success_rate']:.2f},"
        f"{s_all['error_rate']:.2f},"
        f"{s_base['avg_ms']:.2f},"
        f"{s_fault['avg_ms']:.2f},"
        f"{s_after['avg_ms']:.2f},"
        f"{s_fault['max_ms']:.2f},"
        f"{recovered if recovered is not None else 'NA'}"
    )
