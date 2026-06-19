#!/usr/bin/env python3
from pathlib import Path
from statistics import mean, median
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime

BASE = Path("experiments/kubeedge/node-failure/edge")
OUT_CSV = BASE / "edge-node-failure-summary.csv"
OUT_TXT = BASE / "edge-node-failure-summary-aggregate.txt"

def read_kv(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data

def to_float(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None

def to_int(v):
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except Exception:
        return None

def percentile(values, p):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)

def parse_requests(path: Path):
    durations = []
    errors = Counter()
    total = ok = fail = 0
    first_fail = None
    last_fail = None

    if not path.exists():
        return {
            "total": 0,
            "ok": 0,
            "fail": 0,
            "success_rate": 0.0,
            "error_rate": 0.0,
            "median_ms": None,
            "p95_ms": None,
            "max_ms": None,
            "errors": errors,
            "first_fail": "",
            "last_fail": "",
        }

    with path.open(newline="", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            status = row.get("status_code", "")
            success = row.get("success", "")
            err = row.get("error", "")
            start = row.get("request_start_time", "")

            d = to_float(row.get("duration_ms", ""))
            if d is not None:
                durations.append(d)

            is_ok = (status == "200" and success == "True")
            if is_ok:
                ok += 1
            else:
                fail += 1
                errors[err or "unknown"] += 1
                if not first_fail:
                    first_fail = start
                last_fail = start

    success_rate = (ok / total * 100) if total else 0.0
    error_rate = (fail / total * 100) if total else 0.0

    return {
        "total": total,
        "ok": ok,
        "fail": fail,
        "success_rate": success_rate,
        "error_rate": error_rate,
        "median_ms": median(durations) if durations else None,
        "p95_ms": percentile(durations, 95),
        "max_ms": max(durations) if durations else None,
        "errors": errors,
        "first_fail": first_fail or "",
        "last_fail": last_fail or "",
    }

def preflight_ok(path: Path) -> bool:
    if not path.exists():
        return False
    return "Preflight OK" in path.read_text(errors="replace")

def restart_sum(path: Path):
    if not path.exists():
        return None
    total = 0
    lines = path.read_text(errors="replace").splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 4 and parts[0].startswith("nginx-testapp"):
            m = re.match(r"(\d+)", parts[3])
            if m:
                total += int(m.group(1))
    return total

def file_contains(path: Path, pattern: str) -> bool:
    if not path.exists():
        return False
    return pattern in path.read_text(errors="replace")

rows = []
all_errors = Counter()
by_node = defaultdict(list)

run_dirs = sorted(BASE.glob("run-[0-9][0-9]-*"))

for run_dir in run_dirs:
    s = read_kv(run_dir / "summary.txt")
    req = parse_requests(run_dir / "requests.csv")

    run_name = run_dir.name
    failed_node = s.get("failed_node", run_name.split("-")[-1])
    role = s.get("role", "edge")

    restarts_before = restart_sum(run_dir / "pods_before.txt")
    restarts_final = restart_sum(run_dir / "pods_final.txt")
    restart_delta = None
    if restarts_before is not None and restarts_final is not None:
        restart_delta = restarts_final - restarts_before

    errors_text = ";".join(f"{k}:{v}" for k, v in sorted(req["errors"].items()))
    all_errors.update(req["errors"])

    row = {
        "run": run_name,
        "role": role,
        "failed_node": failed_node,
        "url": s.get("url", ""),
        "node_notready_detected": s.get("node_notready_detected", ""),
        "node_ready_detected": s.get("node_ready_detected", ""),
        "node_notready_seconds": to_float(s.get("node_notready_seconds")),
        "node_recovery_seconds": to_float(s.get("node_recovery_seconds")),
        "vm_poweroff_to_ready_seconds": to_float(s.get("vm_poweroff_to_ready_seconds")),
        "vm_restart_to_ready_seconds": to_float(s.get("vm_restart_to_ready_seconds")),
        "total_requests": req["total"],
        "ok_requests": req["ok"],
        "failed_requests": req["fail"],
        "success_rate_percent": req["success_rate"],
        "error_rate_percent": req["error_rate"],
        "median_latency_ms": req["median_ms"],
        "p95_latency_ms": req["p95_ms"],
        "max_latency_ms": req["max_ms"],
        "error_types": errors_text,
        "first_failed_request_time": req["first_fail"],
        "last_failed_request_time": req["last_fail"],
        "pod_restart_delta": restart_delta,
        "preflight_before_ok": preflight_ok(run_dir / "route_preflight_before" / "preflight.log"),
        "preflight_after_ok": preflight_ok(run_dir / "route_preflight_after" / "preflight.log"),
        "manual_intervention": (run_dir / "manual_intervention_prompt.txt").exists(),
        "nodes_final_ready": file_contains(run_dir / "nodes_final.txt", failed_node + "     Ready") or file_contains(run_dir / "nodes_final.txt", failed_node + "   Ready"),
    }

    rows.append(row)
    by_node[failed_node].append(row)

fields = [
    "run", "role", "failed_node", "url",
    "node_notready_detected", "node_ready_detected",
    "node_notready_seconds", "node_recovery_seconds",
    "vm_poweroff_to_ready_seconds", "vm_restart_to_ready_seconds",
    "total_requests", "ok_requests", "failed_requests",
    "success_rate_percent", "error_rate_percent",
    "median_latency_ms", "p95_latency_ms", "max_latency_ms",
    "error_types", "first_failed_request_time", "last_failed_request_time",
    "pod_restart_delta", "preflight_before_ok", "preflight_after_ok",
    "manual_intervention", "nodes_final_ready",
]

with OUT_CSV.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

def nums(key):
    return [r[key] for r in rows if isinstance(r.get(key), (int, float)) and r[key] is not None]

def fmt(v, digits=2):
    if v is None:
        return "n/a"
    return f"{v:.{digits}f}"

def summary_for_node(node):
    rs = by_node[node]
    if not rs:
        return []
    success = [r["success_rate_percent"] for r in rs]
    recovery = [r["node_recovery_seconds"] for r in rs if r["node_recovery_seconds"] is not None]
    restart_ready = [r["vm_restart_to_ready_seconds"] for r in rs if r["vm_restart_to_ready_seconds"] is not None]
    return [
        f"{node}_runs={len(rs)}",
        f"{node}_success_rate_mean_percent={fmt(mean(success))}",
        f"{node}_success_rate_min_percent={fmt(min(success))}",
        f"{node}_recovery_seconds_median={fmt(median(recovery)) if recovery else 'n/a'}",
        f"{node}_recovery_seconds_mean={fmt(mean(recovery)) if recovery else 'n/a'}",
        f"{node}_restart_to_ready_seconds_median={fmt(median(restart_ready)) if restart_ready else 'n/a'}",
    ]

success_rates = nums("success_rate_percent")
error_rates = nums("error_rate_percent")
notready_seconds = nums("node_notready_seconds")
recovery_seconds = nums("node_recovery_seconds")
poweroff_ready = nums("vm_poweroff_to_ready_seconds")
restart_ready = nums("vm_restart_to_ready_seconds")
p95s = nums("p95_latency_ms")
maxs = nums("max_latency_ms")
restart_deltas = nums("pod_restart_delta")

pre_before_ok = sum(1 for r in rows if r["preflight_before_ok"])
pre_after_ok = sum(1 for r in rows if r["preflight_after_ok"])
all_node_ready = all(r["node_ready_detected"] == "true" for r in rows)
all_notready = all(r["node_notready_detected"] == "true" for r in rows)
manual_count = sum(1 for r in rows if r["manual_intervention"])

lines = []
lines.append("# KubeEdge Edge Node Failure Aggregate")
lines.append("")
lines.append(f"runs={len(rows)}")
lines.append(f"all_node_notready_detected={str(all_notready).lower()}")
lines.append(f"all_node_ready_detected={str(all_node_ready).lower()}")
lines.append(f"manual_interventions={manual_count}")
lines.append(f"preflight_before_ok={pre_before_ok}/{len(rows)}")
lines.append(f"preflight_after_ok={pre_after_ok}/{len(rows)}")
lines.append("")
lines.append(f"request_success_rate_mean_percent={fmt(mean(success_rates)) if success_rates else 'n/a'}")
lines.append(f"request_success_rate_median_percent={fmt(median(success_rates)) if success_rates else 'n/a'}")
lines.append(f"request_success_rate_min_percent={fmt(min(success_rates)) if success_rates else 'n/a'}")
lines.append(f"request_success_rate_max_percent={fmt(max(success_rates)) if success_rates else 'n/a'}")
lines.append(f"error_rate_mean_percent={fmt(mean(error_rates)) if error_rates else 'n/a'}")
lines.append(f"error_rate_max_percent={fmt(max(error_rates)) if error_rates else 'n/a'}")
lines.append("")
lines.append(f"node_notready_seconds_median={fmt(median(notready_seconds)) if notready_seconds else 'n/a'}")
lines.append(f"node_notready_seconds_mean={fmt(mean(notready_seconds)) if notready_seconds else 'n/a'}")
lines.append(f"node_notready_seconds_min={fmt(min(notready_seconds)) if notready_seconds else 'n/a'}")
lines.append(f"node_notready_seconds_max={fmt(max(notready_seconds)) if notready_seconds else 'n/a'}")
lines.append("")
lines.append(f"node_recovery_seconds_median={fmt(median(recovery_seconds)) if recovery_seconds else 'n/a'}")
lines.append(f"node_recovery_seconds_mean={fmt(mean(recovery_seconds)) if recovery_seconds else 'n/a'}")
lines.append(f"node_recovery_seconds_min={fmt(min(recovery_seconds)) if recovery_seconds else 'n/a'}")
lines.append(f"node_recovery_seconds_max={fmt(max(recovery_seconds)) if recovery_seconds else 'n/a'}")
lines.append("")
lines.append(f"vm_poweroff_to_ready_seconds_median={fmt(median(poweroff_ready)) if poweroff_ready else 'n/a'}")
lines.append(f"vm_poweroff_to_ready_seconds_mean={fmt(mean(poweroff_ready)) if poweroff_ready else 'n/a'}")
lines.append(f"vm_restart_to_ready_seconds_median={fmt(median(restart_ready)) if restart_ready else 'n/a'}")
lines.append(f"vm_restart_to_ready_seconds_mean={fmt(mean(restart_ready)) if restart_ready else 'n/a'}")
lines.append("")
lines.append(f"p95_latency_ms_median={fmt(median(p95s)) if p95s else 'n/a'}")
lines.append(f"max_latency_ms_max={fmt(max(maxs)) if maxs else 'n/a'}")
lines.append(f"pod_restart_delta_sum={sum(restart_deltas) if restart_deltas else 0}")
lines.append("")
lines.append("error_types=" + ";".join(f"{k}:{v}" for k, v in sorted(all_errors.items())))
lines.append("")

for node in sorted(by_node):
    lines.extend(summary_for_node(node))
    lines.append("")

# simple outlier notes
if success_rates:
    low = [r["run"] for r in rows if r["success_rate_percent"] < mean(success_rates) - 10]
    if low:
        lines.append(f"notice_low_success_runs={','.join(low)}")
if recovery_seconds and len(recovery_seconds) >= 3:
    med = median(recovery_seconds)
    out = [r["run"] for r in rows if r["node_recovery_seconds"] and r["node_recovery_seconds"] > max(300, med * 2)]
    if out:
        lines.append(f"notice_recovery_outliers={','.join(out)}")

OUT_TXT.write_text("\n".join(lines) + "\n")

print(f"Wrote {OUT_CSV}")
print(f"Wrote {OUT_TXT}")
