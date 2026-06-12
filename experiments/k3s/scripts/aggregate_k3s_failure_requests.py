from pathlib import Path
import csv
from statistics import mean, median

BASE = Path("experiments/k3s")

SCENARIO_DIRS = {
    "pod-failure": BASE / "pod-failure",
    "node-failure-worker": BASE / "node-failure/worker",
    "node-failure-server": BASE / "node-failure/server",
}

OUT = BASE / "k3s-failure-summary.csv"

FIELDS = [
    "scenario",
    "run",
    "requests_total",
    "success",
    "failed",
    "success_rate_pct",
    "error_rate_pct",
    "avg_ms",
    "median_ms",
    "p95_ms",
    "p99_ms",
    "min_ms",
    "max_ms",
    "timeouts",
    "node_notready_observed",
    "manual_intervention_observed",
]

def parse_bool_file(run_dir: Path, pattern: str) -> bool:
    return any(run_dir.glob(pattern))

def read_requests(path: Path):
    rows = list(csv.DictReader(path.open(encoding="utf-8", errors="replace")))
    durations = []
    success = 0
    failed = 0
    timeouts = 0

    for r in rows:
        ok = str(r.get("success", "")).strip().lower()
        err = str(r.get("error", "")).strip().lower()

        if ok in {"true", "1", "yes"}:
            success += 1
        else:
            failed += 1

        if "timeout" in err:
            timeouts += 1

        value = r.get("duration_ms", "")
        try:
            durations.append(float(value))
        except (TypeError, ValueError):
            pass

    total = len(rows)

    def percentile(vals, p):
        if not vals:
            return ""
        vals = sorted(vals)
        k = (len(vals) - 1) * (p / 100)
        f = int(k)
        c = min(f + 1, len(vals) - 1)
        if f == c:
            return vals[f]
        return vals[f] + (vals[c] - vals[f]) * (k - f)

    return {
        "requests_total": total,
        "success": success,
        "failed": failed,
        "success_rate_pct": "" if total == 0 else success / total * 100,
        "error_rate_pct": "" if total == 0 else failed / total * 100,
        "avg_ms": "" if not durations else mean(durations),
        "median_ms": "" if not durations else median(durations),
        "p95_ms": "" if not durations else percentile(durations, 95),
        "p99_ms": "" if not durations else percentile(durations, 99),
        "min_ms": "" if not durations else min(durations),
        "max_ms": "" if not durations else max(durations),
        "timeouts": timeouts,
    }

def fmt(v):
    if isinstance(v, float):
        return f"{v:.2f}"
    return v

out_rows = []

for scenario, scenario_dir in SCENARIO_DIRS.items():
    for run_dir in sorted(scenario_dir.glob("run-*")):
        req = run_dir / "requests.csv"
        if not req.exists():
            continue

        data = read_requests(req)

        node_notready = False
        for f in list(run_dir.glob("nodes*.txt")) + list(run_dir.glob("events*.txt")):
            text = f.read_text(encoding="utf-8", errors="replace")
            if "NotReady" in text or "NodeStatusUnknown" in text:
                node_notready = True
                break

        manual = parse_bool_file(run_dir, "manual_intervention*.txt")

        row = {
            "scenario": scenario,
            "run": run_dir.name,
            **data,
            "node_notready_observed": "yes" if node_notready else "no",
            "manual_intervention_observed": "yes" if manual else "no",
        }
        out_rows.append({k: fmt(row.get(k, "")) for k in FIELDS})

with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(out_rows)

print(f"Wrote {OUT} with {len(out_rows)} rows")
