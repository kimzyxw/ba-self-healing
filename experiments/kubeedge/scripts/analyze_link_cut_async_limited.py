#!/usr/bin/env python3
import csv
import re
import statistics as stats
from pathlib import Path
import sys

if len(sys.argv) != 2:
    print("Usage: analyze_link_cut_async_limited.py <scenario-dir>", file=sys.stderr)
    sys.exit(1)

scenario_dir = Path(sys.argv[1])
if not scenario_dir.exists():
    print(f"Scenario directory not found: {scenario_dir}", file=sys.stderr)
    sys.exit(1)

run_dirs = sorted(scenario_dir.glob("run-*-router"))

def parse_value(v):
    v = v.strip()
    if v.endswith("%"):
        return float(v[:-1])
    if v == "NA":
        return None
    try:
        return float(v)
    except ValueError:
        return v

def parse_summary(path):
    data = {}
    current = None

    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue

        m = re.match(r"--- (.+) ---", line)
        if m:
            current = m.group(1).strip().lower()
            data[current] = {}
            continue

        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = parse_value(v)
            if current:
                data[current][k] = v
            else:
                data[k] = v

    return data

rows = []

for run_dir in run_dirs:
    summary = run_dir / "summary.txt"
    if not summary.exists():
        continue

    d = parse_summary(summary)

    row = {
        "run": run_dir.name,
        "scenario": d.get("scenario", scenario_dir.name),
        "duration_s": d.get("duration_s"),
        "baseline_s": d.get("baseline_s"),
        "after_s": d.get("after_s"),
        "timeout_s": d.get("timeout_s"),
        "max_in_flight": d.get("max_in_flight"),
        "router_iface": d.get("router_iface"),
        "router_path_valid": d.get("validation", {}).get("router_path_valid"),
        "link_cut_applied": d.get("validation", {}).get("link_cut_applied"),
        "interface_recovered": d.get("validation", {}).get("interface_recovered"),
        "router_recovery_documented": d.get("validation", {}).get("router_recovery_documented"),
        "recovery_latency_s": d.get("recovery", {}).get("recovery_latency_s"),
    }

    for phase in ["overall", "baseline", "fault", "after"]:
        sec = d.get(phase, {})
        for key in [
            "requests_total",
            "success",
            "failed",
            "success_rate",
            "error_rate",
            "avg_ms",
            "median_ms",
            "p95_ms",
            "p99_ms",
            "min_ms",
            "max_ms",
            "success_median_ms",
            "success_p95_ms",
            "timeouts",
        ]:
            row[f"{phase}_{key}"] = sec.get(key)

        row[f"{phase}_errors"] = sec.get("errors")

    rows.append(row)

if not rows:
    print("No runs found.", file=sys.stderr)
    sys.exit(1)

csv_path = scenario_dir / "link-cut-summary.csv"
agg_path = scenario_dir / "link-cut-summary-aggregate.txt"

fieldnames = list(rows[0].keys())
with csv_path.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

def vals(key):
    out = []
    for r in rows:
        v = r.get(key)
        if isinstance(v, (int, float)):
            out.append(float(v))
    return out

def med(key):
    v = vals(key)
    return stats.median(v) if v else None

def mean(key):
    v = vals(key)
    return stats.mean(v) if v else None

def minv(key):
    v = vals(key)
    return min(v) if v else None

def maxv(key):
    v = vals(key)
    return max(v) if v else None

def fmt(v):
    if v is None:
        return "NA"
    return f"{v:.2f}"

def fmt_s(v):
    if v is None:
        return "NA"
    return f"{v:.2f}"

def count_yes(key):
    return sum(1 for r in rows if r.get(key) == "yes")

scenario = scenario_dir.name
duration = rows[0].get("duration_s")
baseline = rows[0].get("baseline_s")
after = rows[0].get("after_s")
timeout = rows[0].get("timeout_s")
max_in_flight = rows[0].get("max_in_flight")
router_iface = rows[0].get("router_iface")

with agg_path.open("w") as f:
    f.write(f"Runs ausgewertet: {len(rows)}\n")
    f.write(f"scenario={scenario}\n")
    f.write(f"runs={len(rows)}\n")
    f.write(f"router_path_valid={count_yes('router_path_valid')}/{len(rows)}\n")
    f.write(f"link_cut_applied={count_yes('link_cut_applied')}/{len(rows)}\n")
    f.write(f"interface_recovered={count_yes('interface_recovered')}/{len(rows)}\n")
    f.write(f"router_recovery_documented={count_yes('router_recovery_documented')}/{len(rows)}\n")
    f.write(f"duration_s={duration}\n")
    f.write(f"baseline_s={baseline}\n")
    f.write(f"after_s={after}\n")
    f.write(f"timeout_s={timeout}\n")
    f.write(f"max_in_flight={max_in_flight}\n")
    f.write(f"router_iface={router_iface}\n\n")

    for phase in ["overall", "baseline", "fault", "after"]:
        f.write(f"[{phase}]\n")
        f.write(f"{phase}_success_rate_percent_median={fmt(med(f'{phase}_success_rate'))}\n")
        f.write(f"{phase}_success_rate_percent_mean={fmt(mean(f'{phase}_success_rate'))}\n")
        f.write(f"{phase}_error_rate_percent_median={fmt(med(f'{phase}_error_rate'))}\n")
        f.write(f"{phase}_error_rate_percent_mean={fmt(mean(f'{phase}_error_rate'))}\n")
        f.write(f"{phase}_median_ms_median={fmt(med(f'{phase}_median_ms'))}\n")
        f.write(f"{phase}_p95_ms_median={fmt(med(f'{phase}_p95_ms'))}\n")
        f.write(f"{phase}_p99_ms_median={fmt(med(f'{phase}_p99_ms'))}\n")
        f.write(f"{phase}_max_ms_median={fmt(med(f'{phase}_max_ms'))}\n")
        f.write(f"{phase}_timeouts_total={int(sum(vals(f'{phase}_timeouts')))}\n\n")

    f.write("[recovery]\n")
    f.write(f"recovery_latency_s_min={fmt_s(minv('recovery_latency_s'))}\n")
    f.write(f"recovery_latency_s_median={fmt_s(med('recovery_latency_s'))}\n")
    f.write(f"recovery_latency_s_mean={fmt_s(mean('recovery_latency_s'))}\n")
    f.write(f"recovery_latency_s_max={fmt_s(maxv('recovery_latency_s'))}\n")

print(f"Wrote {csv_path}")
print(f"Wrote {agg_path}")
print(f"Runs ausgewertet: {len(rows)}")
