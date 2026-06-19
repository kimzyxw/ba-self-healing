#!/usr/bin/env python3
import csv
import math
from pathlib import Path
from statistics import median, mean

SCENARIO_DIR = Path("experiments/kubeedge/pod-failure")
OUT_CSV = SCENARIO_DIR / "pod-failure-summary.csv"
OUT_AGG = SCENARIO_DIR / "pod-failure-summary-aggregate.txt"


def read_kv(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def percentile(values, p):
    if not values:
        return ""
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    return values[f] * (c - k) + values[c] * (k - f)


def parse_requests(path: Path) -> dict:
    durations = []
    total = 0
    ok = 0
    failed = 0
    status_codes = {}

    if not path.exists():
        return {
            "total_requests": 0,
            "ok_requests": 0,
            "failed_requests": 0,
            "success_rate_percent": 0.0,
            "error_rate_percent": 0.0,
            "median_ms": "",
            "p95_ms": "",
            "max_ms": "",
            "status_codes": "",
        }

    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            status = row.get("status_code", "")
            success = row.get("success", "")
            error = row.get("error", "")

            if status:
                status_codes[status] = status_codes.get(status, 0) + 1
            elif error:
                status_codes[error] = status_codes.get(error, 0) + 1
            else:
                status_codes["unknown"] = status_codes.get("unknown", 0) + 1

            try:
                durations.append(float(row.get("duration_ms", "")))
            except ValueError:
                pass

            if status == "200" and success == "True":
                ok += 1
            else:
                failed += 1

    success_rate = (ok / total * 100) if total else 0.0
    error_rate = (failed / total * 100) if total else 0.0

    return {
        "total_requests": total,
        "ok_requests": ok,
        "failed_requests": failed,
        "success_rate_percent": round(success_rate, 2),
        "error_rate_percent": round(error_rate, 2),
        "median_ms": round(median(durations), 2) if durations else "",
        "p95_ms": round(percentile(durations, 95), 2) if durations else "",
        "max_ms": round(max(durations), 2) if durations else "",
        "status_codes": ";".join(f"{k}:{v}" for k, v in sorted(status_codes.items())),
    }


def sum_restarts_from_pods_file(path: Path) -> int:
    if not path.exists():
        return 0

    lines = path.read_text().splitlines()
    if len(lines) < 2:
        return 0

    restarts = 0
    for line in lines[1:]:
        parts = line.split()
        # kubectl get pods -o wide:
        # NAME READY STATUS RESTARTS AGE IP NODE ...
        if len(parts) >= 4:
            try:
                restarts += int(parts[3])
            except ValueError:
                pass
    return restarts


def node_status_summary(path: Path) -> str:
    if not path.exists():
        return ""

    lines = path.read_text().splitlines()
    if len(lines) < 2:
        return ""

    statuses = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 2:
            statuses.append(f"{parts[0]}:{parts[1]}")
    return ";".join(statuses)


def kubeedge_component_summary(path: Path) -> str:
    if not path.exists():
        return ""

    lines = path.read_text().splitlines()
    if len(lines) < 2:
        return ""

    components = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 3:
            components.append(f"{parts[0]}:{parts[1]}:{parts[2]}")
    return ";".join(components)


rows = []

for run_dir in sorted(SCENARIO_DIR.glob("run-*")):
    if not run_dir.is_dir():
        continue

    summary = read_kv(run_dir / "summary.txt")
    req = parse_requests(run_dir / "requests.csv")

    row = {
        "run": run_dir.name,
        "deleted_pod": summary.get("deleted_pod", ""),
        "deleted_pod_node": summary.get("deleted_pod_node", ""),
        "recovered": summary.get("recovered", ""),
        "recovery_seconds": summary.get("recovery_seconds", ""),
        "total_requests": req["total_requests"],
        "ok_requests": req["ok_requests"],
        "failed_requests": req["failed_requests"],
        "success_rate_percent": req["success_rate_percent"],
        "error_rate_percent": req["error_rate_percent"],
        "median_ms": req["median_ms"],
        "p95_ms": req["p95_ms"],
        "max_ms": req["max_ms"],
        "status_codes": req["status_codes"],
        "pod_restarts_before": sum_restarts_from_pods_file(run_dir / "pods_before.txt"),
        "pod_restarts_after": sum_restarts_from_pods_file(run_dir / "pods_after.txt"),
        "node_status_before": node_status_summary(run_dir / "nodes_before.txt"),
        "node_status_after": node_status_summary(run_dir / "nodes_after.txt"),
        "kubeedge_components_after": kubeedge_component_summary(run_dir / "kubeedge_pods_after.txt"),
    }
    rows.append(row)

fieldnames = [
    "run",
    "deleted_pod",
    "deleted_pod_node",
    "recovered",
    "recovery_seconds",
    "total_requests",
    "ok_requests",
    "failed_requests",
    "success_rate_percent",
    "error_rate_percent",
    "median_ms",
    "p95_ms",
    "max_ms",
    "status_codes",
    "pod_restarts_before",
    "pod_restarts_after",
    "node_status_before",
    "node_status_after",
    "kubeedge_components_after",
]

with OUT_CSV.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

recovery_values = []
success_values = []
error_values = []
p95_values = []
max_values = []
all_recovered = True

for row in rows:
    try:
        recovery_values.append(float(row["recovery_seconds"]))
    except ValueError:
        pass
    try:
        success_values.append(float(row["success_rate_percent"]))
    except ValueError:
        pass
    try:
        error_values.append(float(row["error_rate_percent"]))
    except ValueError:
        pass
    try:
        p95_values.append(float(row["p95_ms"]))
    except ValueError:
        pass
    try:
        max_values.append(float(row["max_ms"]))
    except ValueError:
        pass
    if row["recovered"] != "true":
        all_recovered = False

outlier_note = ""
if recovery_values:
    med = median(recovery_values)
    slow = [v for v in recovery_values if v > max(10, med * 3)]
    if slow:
        outlier_note = (
            "Hinweis: Mindestens ein Lauf zeigt eine deutlich längere Recovery Time "
            f"als der Median. Werte: {slow}. Diese Läufe sollten anhand der Events "
            "geprüft und nicht ohne technische Begründung ausgeschlossen werden."
        )

aggregate_text = f"""# KubeEdge Pod Failure Aggregate

runs={len(rows)}
all_recovered={str(all_recovered).lower()}

request_success_rate_mean_percent={round(mean(success_values), 2) if success_values else ""}
request_success_rate_min_percent={round(min(success_values), 2) if success_values else ""}
error_rate_mean_percent={round(mean(error_values), 2) if error_values else ""}
error_rate_max_percent={round(max(error_values), 2) if error_values else ""}

recovery_seconds_median={round(median(recovery_values), 2) if recovery_values else ""}
recovery_seconds_mean={round(mean(recovery_values), 2) if recovery_values else ""}
recovery_seconds_min={round(min(recovery_values), 2) if recovery_values else ""}
recovery_seconds_max={round(max(recovery_values), 2) if recovery_values else ""}

p95_latency_ms_median={round(median(p95_values), 2) if p95_values else ""}
max_latency_ms_max={round(max(max_values), 2) if max_values else ""}

{outlier_note}
"""

OUT_AGG.write_text(aggregate_text)

print(f"Wrote {OUT_CSV}")
print(f"Wrote {OUT_AGG}")
print()
print(aggregate_text)
