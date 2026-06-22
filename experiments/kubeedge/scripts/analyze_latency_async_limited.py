#!/usr/bin/env python3
import argparse
import csv
import statistics as stats
from pathlib import Path
from datetime import datetime
from collections import Counter
import math

parser = argparse.ArgumentParser()
parser.add_argument("scenario_dir", help="z.B. experiments/kubeedge/latency-tests/latency-1s-async-limited")
args = parser.parse_args()

SCENARIO = Path(args.scenario_dir)
OUT_CSV = SCENARIO / "latency-summary.csv"
OUT_TXT = SCENARIO / "latency-summary-aggregate.txt"

def t(s):
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))

def pct(vals, p):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    k = (len(vals) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vals[int(k)]
    return vals[f] + (vals[c] - vals[f]) * (k - f)

def fmt(v, digits=2):
    if v is None:
        return "NA"
    return f"{v:.{digits}f}"

def read_file(path, default=""):
    return path.read_text(errors="replace").strip() if path.exists() else default

def read_requests(path):
    rows = []
    with open(path, newline="", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append({
                    "id": r.get("request_id", ""),
                    "start": t(r["request_start_time"]),
                    "end": t(r["request_end_time"]),
                    "status": r.get("status_code", ""),
                    "ms": float(r["duration_ms"]) if r.get("duration_ms") else None,
                    "success": r.get("success") == "True",
                    "error": r.get("error", ""),
                })
            except Exception:
                pass
    return rows

def summarize(rows):
    total = len(rows)
    ok = sum(1 for r in rows if r["success"])
    fail = total - ok
    vals = [r["ms"] for r in rows if r["ms"] is not None]
    success_vals = [r["ms"] for r in rows if r["success"] and r["ms"] is not None]
    fail_vals = [r["ms"] for r in rows if not r["success"] and r["ms"] is not None]
    errors = Counter((r["error"] or "unknown") for r in rows if not r["success"])

    return {
        "total": total,
        "ok": ok,
        "fail": fail,
        "success_rate": ok / total * 100 if total else None,
        "error_rate": fail / total * 100 if total else None,
        "avg": stats.mean(vals) if vals else None,
        "median": stats.median(vals) if vals else None,
        "p95": pct(vals, 95),
        "p99": pct(vals, 99),
        "min": min(vals) if vals else None,
        "max": max(vals) if vals else None,
        "success_median": stats.median(success_vals) if success_vals else None,
        "success_p95": pct(success_vals, 95),
        "fail_median": stats.median(fail_vals) if fail_vals else None,
        "gt_10s": sum(v > 10_000 for v in vals),
        "gt_60s": sum(v > 60_000 for v in vals),
        "gt_120s": sum(v > 120_000 for v in vals),
        "gt_300s": sum(v > 300_000 for v in vals),
        "errors": errors,
    }

def parse_summary_value(path, key):
    text = read_file(path)
    for line in text.splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""

def parse_float_or_none(v):
    try:
        if not v or v == "NA":
            return None
        return float(v)
    except Exception:
        return None

def preflight_ok(run_dir, which):
    return "Preflight OK" in read_file(run_dir / f"route_preflight_{which}" / "preflight.log")

runs = []

for run_dir in sorted(SCENARIO.glob("run-*-router")):
    fault_path = run_dir / "fault_time.txt"
    recovery_path = run_dir / "recovery_time.txt"
    requests_path = run_dir / "requests.csv"

    if not fault_path.exists() or not recovery_path.exists() or not requests_path.exists():
        continue

    fault = t(fault_path.read_text())
    recovery = t(recovery_path.read_text())
    start = t(read_file(run_dir / "test_start_time.txt"))
    end = t(read_file(run_dir / "test_end_time.txt"))

    rows = read_requests(requests_path)
    baseline = [r for r in rows if r["start"] < fault]
    fault_rows = [r for r in rows if fault <= r["start"] < recovery]
    after = [r for r in rows if r["start"] >= recovery]

    traceroute = read_file(run_dir / "traceroute_before.txt")
    tc_during = read_file(run_dir / "tc_during.txt")
    tc_after = read_file(run_dir / "tc_after.txt")

    recovery_latency = None
    for r in after:
        if r["success"] and r["ms"] is not None and r["ms"] < 500:
            recovery_latency = (r["end"] - recovery).total_seconds()
            break

    fault_summary = summarize(fault_rows)

    runs.append({
        "name": run_dir.name,
        "delay": read_file(run_dir / "delay.txt"),
        "duration": read_file(run_dir / "duration_seconds.txt"),
        "baseline_s": read_file(run_dir / "baseline_seconds.txt"),
        "after_s": read_file(run_dir / "after_seconds.txt"),
        "timeout": read_file(run_dir / "timeout_seconds.txt"),
        "max_in_flight": read_file(run_dir / "max_in_flight.txt", "NA"),
        "router_ifaces": read_file(run_dir / "affected_interface.txt"),
        "run_duration_s": (end - start).total_seconds(),
        "valid_router": "10.10.10.136" in traceroute,
        "valid_tc": "netem" in tc_during and read_file(run_dir / "delay.txt") in tc_during,
        "valid_cleanup": "netem" not in tc_after,
        "preflight_before_ok": preflight_ok(run_dir, "before"),
        "preflight_after_ok": preflight_ok(run_dir, "after"),
        "overall": summarize(rows),
        "baseline": summarize(baseline),
        "fault": fault_summary,
        "after": summarize(after),
        "recovery_latency": recovery_latency,
    })

fields = [
    "run", "delay", "duration_s", "baseline_s", "after_s", "timeout_s", "max_in_flight",
    "router_ifaces", "run_duration_s",
    "preflight_before_ok", "preflight_after_ok", "router_path_valid", "tc_active", "tc_cleanup",
    "overall_total", "overall_success_rate", "overall_error_rate", "overall_median_ms", "overall_p95_ms", "overall_max_ms",
    "baseline_success_rate", "baseline_median_ms", "baseline_p95_ms",
    "fault_total", "fault_success_rate", "fault_error_rate", "fault_median_ms", "fault_p95_ms", "fault_p99_ms", "fault_max_ms",
    "fault_gt_10s", "fault_gt_60s", "fault_gt_120s", "fault_gt_300s",
    "after_success_rate", "after_median_ms", "after_p95_ms",
    "recovery_latency_s",
    "fault_errors",
]

with OUT_CSV.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for r in runs:
        fault_errors = ";".join(f"{k}:{v}" for k, v in sorted(r["fault"]["errors"].items())) or "none"
        writer.writerow({
            "run": r["name"],
            "delay": r["delay"],
            "duration_s": r["duration"],
            "baseline_s": r["baseline_s"],
            "after_s": r["after_s"],
            "timeout_s": r["timeout"],
            "max_in_flight": r["max_in_flight"],
            "router_ifaces": r["router_ifaces"],
            "run_duration_s": f"{r['run_duration_s']:.2f}",
            "preflight_before_ok": r["preflight_before_ok"],
            "preflight_after_ok": r["preflight_after_ok"],
            "router_path_valid": r["valid_router"],
            "tc_active": r["valid_tc"],
            "tc_cleanup": r["valid_cleanup"],
            "overall_total": r["overall"]["total"],
            "overall_success_rate": fmt(r["overall"]["success_rate"]),
            "overall_error_rate": fmt(r["overall"]["error_rate"]),
            "overall_median_ms": fmt(r["overall"]["median"]),
            "overall_p95_ms": fmt(r["overall"]["p95"]),
            "overall_max_ms": fmt(r["overall"]["max"]),
            "baseline_success_rate": fmt(r["baseline"]["success_rate"]),
            "baseline_median_ms": fmt(r["baseline"]["median"]),
            "baseline_p95_ms": fmt(r["baseline"]["p95"]),
            "fault_total": r["fault"]["total"],
            "fault_success_rate": fmt(r["fault"]["success_rate"]),
            "fault_error_rate": fmt(r["fault"]["error_rate"]),
            "fault_median_ms": fmt(r["fault"]["median"]),
            "fault_p95_ms": fmt(r["fault"]["p95"]),
            "fault_p99_ms": fmt(r["fault"]["p99"]),
            "fault_max_ms": fmt(r["fault"]["max"]),
            "fault_gt_10s": r["fault"]["gt_10s"],
            "fault_gt_60s": r["fault"]["gt_60s"],
            "fault_gt_120s": r["fault"]["gt_120s"],
            "fault_gt_300s": r["fault"]["gt_300s"],
            "after_success_rate": fmt(r["after"]["success_rate"]),
            "after_median_ms": fmt(r["after"]["median"]),
            "after_p95_ms": fmt(r["after"]["p95"]),
            "recovery_latency_s": fmt(r["recovery_latency"]),
            "fault_errors": fault_errors,
        })

def nums(section, key):
    return [r[section][key] for r in runs if r[section][key] is not None]

def nums_top(key):
    return [r[key] for r in runs if r[key] is not None]

def stat_line(name, values):
    values = [v for v in values if v is not None]
    if not values:
        return [
            f"{name}_min=NA",
            f"{name}_median=NA",
            f"{name}_mean=NA",
            f"{name}_max=NA",
        ]
    return [
        f"{name}_min={fmt(min(values))}",
        f"{name}_median={fmt(stats.median(values))}",
        f"{name}_mean={fmt(stats.mean(values))}",
        f"{name}_max={fmt(max(values))}",
    ]

all_fault_errors = Counter()
for r in runs:
    all_fault_errors.update(r["fault"]["errors"])

lines = []
lines.append(f"# KubeEdge Latency Aggregate: {SCENARIO.name}")
lines.append("")
lines.append(f"runs={len(runs)}")
lines.append(f"preflight_before_ok={sum(r['preflight_before_ok'] for r in runs)}/{len(runs)}")
lines.append(f"preflight_after_ok={sum(r['preflight_after_ok'] for r in runs)}/{len(runs)}")
lines.append(f"router_path_valid={sum(r['valid_router'] for r in runs)}/{len(runs)}")
lines.append(f"tc_active={sum(r['valid_tc'] for r in runs)}/{len(runs)}")
lines.append(f"tc_cleanup={sum(r['valid_cleanup'] for r in runs)}/{len(runs)}")
if runs:
    lines.append(f"delay={runs[0]['delay']}")
    lines.append(f"duration_s={runs[0]['duration']}")
    lines.append(f"baseline_s={runs[0]['baseline_s']}")
    lines.append(f"after_s={runs[0]['after_s']}")
    lines.append(f"timeout_s={runs[0]['timeout']}")
    lines.append(f"max_in_flight={runs[0]['max_in_flight']}")
    lines.append(f"router_ifaces={runs[0]['router_ifaces']}")
lines.append("")
lines.extend(stat_line("run_duration_s", nums_top("run_duration_s")))
lines.append("")
lines.extend(stat_line("overall_success_rate_percent", nums("overall", "success_rate")))
lines.extend(stat_line("overall_error_rate_percent", nums("overall", "error_rate")))
lines.extend(stat_line("overall_median_ms", nums("overall", "median")))
lines.extend(stat_line("overall_p95_ms", nums("overall", "p95")))
lines.append("")
lines.extend(stat_line("baseline_median_ms", nums("baseline", "median")))
lines.extend(stat_line("fault_success_rate_percent", nums("fault", "success_rate")))
lines.extend(stat_line("fault_error_rate_percent", nums("fault", "error_rate")))
lines.extend(stat_line("fault_median_ms", nums("fault", "median")))
lines.extend(stat_line("fault_p95_ms", nums("fault", "p95")))
lines.extend(stat_line("fault_p99_ms", nums("fault", "p99")))
lines.extend(stat_line("fault_max_ms", nums("fault", "max")))
lines.append("")
lines.extend(stat_line("after_median_ms", nums("after", "median")))
lines.extend(stat_line("recovery_latency_s", nums_top("recovery_latency")))
lines.append("")
lines.append(f"total_requests={sum(r['overall']['total'] for r in runs)}")
lines.append(f"total_failed_requests={sum(r['overall']['fail'] for r in runs)}")
lines.append("fault_error_types=" + (";".join(f"{k}:{v}" for k, v in sorted(all_fault_errors.items())) if all_fault_errors else "none"))

OUT_TXT.write_text("\n".join(lines) + "\n")

print(f"Wrote {OUT_CSV}")
print(f"Wrote {OUT_TXT}")
print(f"Runs ausgewertet: {len(runs)}")
