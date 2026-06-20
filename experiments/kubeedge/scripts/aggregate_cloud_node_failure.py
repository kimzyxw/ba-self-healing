#!/usr/bin/env python3
from pathlib import Path
from statistics import mean, median
from collections import Counter, defaultdict
import csv
import re
import math

BASE = Path("experiments/kubeedge/node-failure/cloud")
OUT_CSV = BASE / "cloud-node-failure-summary.csv"
OUT_TXT = BASE / "cloud-node-failure-summary-aggregate.txt"

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

def percentile(values, p):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    return values[f] + (values[c] - values[f]) * (k - f)

def parse_requests(path: Path):
    durations_all = []
    durations_ok = []
    errors = Counter()
    total = ok = fail = 0
    first_fail = ""
    last_fail = ""

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
                durations_all.append(d)

            is_ok = (status == "200" and success == "True")
            if is_ok:
                ok += 1
                if d is not None:
                    durations_ok.append(d)
            else:
                fail += 1
                errors[err or "unknown"] += 1
                if not first_fail:
                    first_fail = start
                last_fail = start

    success_rate = (ok / total * 100) if total else 0.0
    error_rate = (fail / total * 100) if total else 0.0

    # Für Latenzmetriken verwenden wir erfolgreiche Requests.
    return {
        "total": total,
        "ok": ok,
        "fail": fail,
        "success_rate": success_rate,
        "error_rate": error_rate,
        "median_ms": median(durations_ok) if durations_ok else None,
        "p95_ms": percentile(durations_ok, 95),
        "max_ms": max(durations_ok) if durations_ok else None,
        "errors": errors,
        "first_fail": first_fail,
        "last_fail": last_fail,
    }

def preflight_ok(path: Path) -> bool:
    if not path.exists():
        return False
    return "Preflight OK" in path.read_text(errors="replace")

def restart_sum(path: Path):
    if not path.exists():
        return None
    total = 0
    for line in path.read_text(errors="replace").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 4 and parts[0].startswith("nginx-testapp"):
            m = re.match(r"(\d+)", parts[3])
            if m:
                total += int(m.group(1))
    return total

def has_manual_prompt(run_dir: Path) -> bool:
    return (run_dir / "manual_intervention_prompt.txt").exists() or (run_dir / "manual_intervention_prompt_time.txt").exists()

def has_confirmed_manual_intervention(run_dir: Path) -> bool:
    f = run_dir / "manual_intervention.txt"
    if not f.exists():
        return False
    text = f.read_text(errors="replace").lower()
    return (
        "bestaetigt=true" in text
        or "confirmed=true" in text
        or "manueller_eingriff=true" in text
        or "manual_intervention=true" in text
    )

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

    restarts_before = restart_sum(run_dir / "pods_before.txt")
    restarts_final = restart_sum(run_dir / "pods_final.txt")
    restart_delta = ""
    if restarts_before is not None and restarts_final is not None:
        restart_delta = restarts_final - restarts_before

    errors_text = ";".join(f"{k}:{v}" for k, v in sorted(req["errors"].items()))
    all_errors.update(req["errors"])

    row = {
        "run": run_name,
        "role": s.get("role", "cloud"),
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
        "manual_prompt_reached": has_manual_prompt(run_dir),
        "manual_intervention_confirmed": has_confirmed_manual_intervention(run_dir),
        "preflight_before_ok": preflight_ok(run_dir / "route_preflight_before" / "preflight.log"),
        "preflight_after_ok": preflight_ok(run_dir / "route_preflight_after" / "preflight.log"),
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
    "pod_restart_delta", "manual_prompt_reached", "manual_intervention_confirmed",
    "preflight_before_ok", "preflight_after_ok", "nodes_final_ready",
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

def stat_lines(name, values):
    values = [v for v in values if v is not None]
    if not values:
        return [
            f"{name}_min=n/a",
            f"{name}_median=n/a",
            f"{name}_mean=n/a",
            f"{name}_max=n/a",
        ]
    return [
        f"{name}_min={fmt(min(values))}",
        f"{name}_median={fmt(median(values))}",
        f"{name}_mean={fmt(mean(values))}",
        f"{name}_max={fmt(max(values))}",
    ]

lines = []
lines.append("# KubeEdge Cloud Node Failure Aggregate")
lines.append("")
lines.append(f"runs={len(rows)}")
lines.append(f"all_node_notready_detected={str(all(r['node_notready_detected'] == 'true' for r in rows)).lower()}")
lines.append(f"all_node_ready_detected={str(all(r['node_ready_detected'] == 'true' for r in rows)).lower()}")
lines.append(f"manual_prompt_reached_count={sum(1 for r in rows if r['manual_prompt_reached'])}")
lines.append(f"manual_intervention_confirmed_count={sum(1 for r in rows if r['manual_intervention_confirmed'])}")
lines.append(f"preflight_before_ok={sum(1 for r in rows if r['preflight_before_ok'])}/{len(rows)}")
lines.append(f"preflight_after_ok={sum(1 for r in rows if r['preflight_after_ok'])}/{len(rows)}")
lines.append("")
lines.extend(stat_lines("request_success_rate_percent", nums("success_rate_percent")))
lines.extend(stat_lines("error_rate_percent", nums("error_rate_percent")))
lines.append("")
lines.extend(stat_lines("node_notready_seconds", nums("node_notready_seconds")))
lines.extend(stat_lines("node_recovery_seconds", nums("node_recovery_seconds")))
lines.extend(stat_lines("vm_poweroff_to_ready_seconds", nums("vm_poweroff_to_ready_seconds")))
lines.extend(stat_lines("vm_restart_to_ready_seconds", nums("vm_restart_to_ready_seconds")))
lines.append("")
lines.extend(stat_lines("median_latency_ms", nums("median_latency_ms")))
lines.extend(stat_lines("p95_latency_ms", nums("p95_latency_ms")))
lines.extend(stat_lines("max_latency_ms", nums("max_latency_ms")))
lines.append("")
lines.append(f"total_requests={sum(r['total_requests'] for r in rows)}")
lines.append(f"ok_requests={sum(r['ok_requests'] for r in rows)}")
lines.append(f"failed_requests={sum(r['failed_requests'] for r in rows)}")
lines.append("error_types=" + (";".join(f"{k}:{v}" for k, v in sorted(all_errors.items())) if all_errors else "none"))
lines.append("")

for node in sorted(by_node):
    rs = by_node[node]
    success = [r["success_rate_percent"] for r in rs]
    recovery = [r["node_recovery_seconds"] for r in rs if r["node_recovery_seconds"] is not None]
    restart_ready = [r["vm_restart_to_ready_seconds"] for r in rs if r["vm_restart_to_ready_seconds"] is not None]
    notready = [r["node_notready_seconds"] for r in rs if r["node_notready_seconds"] is not None]

    lines.append(f"{node}_runs={len(rs)}")
    lines.append(f"{node}_success_rate_mean_percent={fmt(mean(success)) if success else 'n/a'}")
    lines.append(f"{node}_success_rate_min_percent={fmt(min(success)) if success else 'n/a'}")
    lines.append(f"{node}_node_notready_seconds_median={fmt(median(notready)) if notready else 'n/a'}")
    lines.append(f"{node}_node_recovery_seconds_median={fmt(median(recovery)) if recovery else 'n/a'}")
    lines.append(f"{node}_vm_restart_to_ready_seconds_median={fmt(median(restart_ready)) if restart_ready else 'n/a'}")
    lines.append("")

OUT_TXT.write_text("\n".join(lines) + "\n")

print(f"Wrote {OUT_CSV}")
print(f"Wrote {OUT_TXT}")
