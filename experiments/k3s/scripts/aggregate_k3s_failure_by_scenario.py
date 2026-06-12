from pathlib import Path
import csv
from statistics import mean, median

BASE = Path("experiments/k3s")
INP = BASE / "k3s-failure-summary.csv"
OUT = BASE / "k3s-failure-summary-by-scenario.csv"

def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

rows = list(csv.DictReader(INP.open(encoding="utf-8")))
groups = {}
for r in rows:
    groups.setdefault(r["scenario"], []).append(r)

fields = [
    "scenario",
    "runs",
    "avg_requests_total",
    "avg_success_rate_pct",
    "avg_error_rate_pct",
    "avg_median_ms",
    "avg_p95_ms",
    "avg_p99_ms",
    "avg_timeouts",
    "notready_runs",
    "manual_intervention_runs",
]

out_rows = []

for scenario, items in sorted(groups.items()):
    def avg(name):
        vals = [f(r.get(name, "")) for r in items]
        vals = [v for v in vals if v is not None]
        return "" if not vals else f"{mean(vals):.2f}"

    out_rows.append({
        "scenario": scenario,
        "runs": len(items),
        "avg_requests_total": avg("requests_total"),
        "avg_success_rate_pct": avg("success_rate_pct"),
        "avg_error_rate_pct": avg("error_rate_pct"),
        "avg_median_ms": avg("median_ms"),
        "avg_p95_ms": avg("p95_ms"),
        "avg_p99_ms": avg("p99_ms"),
        "avg_timeouts": avg("timeouts"),
        "notready_runs": sum(1 for r in items if r.get("node_notready_observed") == "yes"),
        "manual_intervention_runs": sum(1 for r in items if r.get("manual_intervention_observed") == "yes"),
    })

with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(out_rows)

print(f"Wrote {OUT} with {len(out_rows)} rows")
