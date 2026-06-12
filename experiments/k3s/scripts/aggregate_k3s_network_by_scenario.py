from pathlib import Path
import csv
from statistics import mean, median

BASE = Path("experiments/k3s")
inp = BASE / "k3s-network-summary.csv"
out = BASE / "k3s-network-summary-by-scenario.csv"

def parse_float(value):
    if value is None or value == "" or value == "NA":
        return None
    value = value.strip().replace("%", "")
    try:
        return float(value)
    except ValueError:
        return None

rows = list(csv.DictReader(inp.open(encoding="utf-8")))

groups = {}
for row in rows:
    key = (row["scenario"], row["phase"])
    groups.setdefault(key, []).append(row)

fields = [
    "scenario",
    "phase",
    "runs",
    "avg_requests_total",
    "avg_success_rate_pct",
    "avg_error_rate_pct",
    "avg_median_ms",
    "avg_p95_ms",
    "avg_p99_ms",
    "avg_timeouts",
    "avg_recovery_latency_s",
    "median_recovery_latency_s",
]

out_rows = []

for (scenario, phase), items in sorted(groups.items()):
    def avg_field(name):
        vals = [parse_float(r.get(name, "")) for r in items]
        vals = [v for v in vals if v is not None]
        return "" if not vals else f"{mean(vals):.2f}"

    rec_vals = [parse_float(r.get("recovery_latency_s", "")) for r in items]
    rec_vals = [v for v in rec_vals if v is not None]

    out_rows.append({
        "scenario": scenario,
        "phase": phase,
        "runs": len(items),
        "avg_requests_total": avg_field("requests_total"),
        "avg_success_rate_pct": avg_field("success_rate"),
        "avg_error_rate_pct": avg_field("error_rate"),
        "avg_median_ms": avg_field("median_ms"),
        "avg_p95_ms": avg_field("p95_ms"),
        "avg_p99_ms": avg_field("p99_ms"),
        "avg_timeouts": avg_field("timeouts"),
        "avg_recovery_latency_s": "" if not rec_vals else f"{mean(rec_vals):.2f}",
        "median_recovery_latency_s": "" if not rec_vals else f"{median(rec_vals):.2f}",
    })

with out.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(out_rows)

print(f"Wrote {out} with {len(out_rows)} rows")
