from pathlib import Path
import csv
import re

BASE = Path("experiments/k3s")

SCENARIOS = [
    BASE / "latency-tests/latency-1s-short",
    BASE / "latency-tests/latency-1min-short",
    BASE / "latency-tests/latency-10min-async-limited",
    BASE / "latency-tests/latency-30min-async-limited",

    BASE / "packet-loss-tests/packet-loss-1pct-async-limited",
    BASE / "packet-loss-tests/packet-loss-10pct-async-limited",
    BASE / "packet-loss-tests/packet-loss-50pct-async-limited",
    BASE / "packet-loss-tests/packet-loss-70pct-router-cleanup",
    BASE / "packet-loss-tests/packet-loss-100pct-safety-cleanup",

    BASE / "link-cut-tests/link-cut-1s",
    BASE / "link-cut-tests/link-cut-1min",
    BASE / "link-cut-tests/link-cut-10min",
    BASE / "link-cut-tests/link-cut-30min",
]

FIELDS = [
    "scenario",
    "run",
    "phase",
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
    "timeouts",
    "recovery_latency_s",
]

def parse_summary(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    scenario = None
    run = path.parent.name
    phase = None
    rows = []
    current = {}

    recovery_latency_s = ""

    for line in text:
        line = line.strip()

        if line.startswith("scenario="):
            scenario = line.split("=", 1)[1]
        elif line.startswith("run="):
            run = line.split("=", 1)[1]
        elif line.startswith("--- ") and line.endswith(" ---"):
            if phase and current:
                rows.append((phase, current))
                current = {}
            phase = line.replace("---", "").strip()
        elif "=" in line and phase:
            key, value = line.split("=", 1)
            current[key.strip()] = value.strip()

    if phase and current:
        rows.append((phase, current))

    # recovery_latency_s steht meist in eigener recovery-Phase.
    for ph, data in rows:
        if "recovery_latency_s" in data:
            recovery_latency_s = data["recovery_latency_s"]

    result = []
    for ph, data in rows:
        if ph not in {"overall", "baseline", "fault", "after"}:
            continue
        row = {field: "" for field in FIELDS}
        row["scenario"] = scenario or path.parent.parent.name
        row["run"] = run
        row["phase"] = ph
        row["recovery_latency_s"] = recovery_latency_s
        for key in FIELDS:
            if key in data:
                row[key] = data[key]
        result.append(row)

    return result

all_rows = []

for scenario_dir in SCENARIOS:
    if not scenario_dir.exists():
        print(f"WARNING: missing {scenario_dir}")
        continue
    for summary in sorted(scenario_dir.glob("run-*/summary.txt")):
        all_rows.extend(parse_summary(summary))

out = BASE / "k3s-network-summary.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"Wrote {out} with {len(all_rows)} rows")
