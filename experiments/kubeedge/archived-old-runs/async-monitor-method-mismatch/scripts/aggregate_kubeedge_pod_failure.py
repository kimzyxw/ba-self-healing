#!/usr/bin/env python3
from pathlib import Path
import csv
from statistics import mean, median
from datetime import datetime
from collections import Counter

BASE = Path("experiments/kubeedge/pod-failure")
OUT_DETAIL = BASE / "pod-failure-summary.csv"
OUT_AGG = BASE / "pod-failure-summary-aggregate.csv"

# run-06 was completed, but contains only 62 requests instead of 180
# because of a timing anomaly. It is kept in the detailed CSV, but excluded
# from the regular quantitative aggregate.
EXCLUDE_FROM_REGULAR_EVALUATION = {"run-06"}


def read_time(path: Path):
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def percentile(vals, p):
    if not vals:
        return None
    vals = sorted(vals)
    k = (len(vals) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[f]
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def fmt_float(value):
    if value is None:
        return ""
    return f"{value:.2f}"


def pods_after_ready(run_dir: Path) -> str:
    pods_after = run_dir / "pods_after.txt"
    if not pods_after.exists():
        return "no"

    lines = [
        line for line in pods_after.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith("nginx-testapp") and "1/1" in line and "Running" in line
    ]
    return "yes" if len(lines) == 3 else "no"


def parse_run(run_dir: Path):
    req = run_dir / "requests.csv"
    if not req.exists():
        return None

    rows = list(csv.DictReader(req.open(encoding="utf-8", errors="replace")))
    durations = []
    success = 0
    failed = 0
    errors = Counter()

    for row in rows:
        ok = str(row.get("success", "")).strip().lower() in {"true", "1", "yes"}

        if ok:
            success += 1
        else:
            failed += 1
            err = str(row.get("error", "")).strip()
            errors[err or "unknown"] += 1

        try:
            durations.append(float(row.get("duration_ms", "")))
        except ValueError:
            pass

    total = len(rows)

    fault = read_time(run_dir / "fault_time.txt")
    recovery = read_time(run_dir / "recovery_time.txt")

    recovery_seconds = None
    if fault and recovery:
        recovery_seconds = round((recovery - fault).total_seconds(), 2)

    deleted_pod = ""
    deleted_pod_file = run_dir / "deleted_pod.txt"
    if deleted_pod_file.exists():
        deleted_pod = deleted_pod_file.read_text(encoding="utf-8", errors="replace").strip()

    included = run_dir.name not in EXCLUDE_FROM_REGULAR_EVALUATION

    return {
        "run": run_dir.name,
        "requests": total,
        "success": success,
        "failed": failed,
        "success_rate_pct": None if total == 0 else success / total * 100,
        "error_rate_pct": None if total == 0 else failed / total * 100,
        "median_ms": None if not durations else median(durations),
        "p95_ms": None if not durations else percentile(durations, 95),
        "min_ms": None if not durations else min(durations),
        "max_ms": None if not durations else max(durations),
        "errors": dict(errors),
        "recovery_seconds": recovery_seconds,
        "deleted_pod": deleted_pod,
        "complete_180_requests": "yes" if total == 180 else "no",
        "pods_after_running_ready": pods_after_ready(run_dir),
        "included_in_regular_evaluation": "yes" if included else "no",
        "_durations": durations,
    }


def write_detail(rows):
    fields = [
        "run",
        "requests",
        "success",
        "failed",
        "success_rate_pct",
        "error_rate_pct",
        "median_ms",
        "p95_ms",
        "min_ms",
        "max_ms",
        "errors",
        "recovery_seconds",
        "deleted_pod",
        "complete_180_requests",
        "pods_after_running_ready",
        "included_in_regular_evaluation",
    ]

    with OUT_DETAIL.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            out = dict(row)
            out.pop("_durations", None)

            for key in [
                "success_rate_pct",
                "error_rate_pct",
                "median_ms",
                "p95_ms",
                "min_ms",
                "max_ms",
            ]:
                out[key] = fmt_float(out[key])

            writer.writerow(out)


def write_aggregate(rows):
    regular = [r for r in rows if r["included_in_regular_evaluation"] == "yes"]

    all_durations = []
    recovery_values = []

    for row in regular:
        all_durations.extend(row["_durations"])
        if row["recovery_seconds"] is not None:
            recovery_values.append(row["recovery_seconds"])

    requests_total = sum(r["requests"] for r in regular)
    success = sum(r["success"] for r in regular)
    failed = sum(r["failed"] for r in regular)

    aggregate = {
        "runs_counted": len(regular),
        "requests_total": requests_total,
        "success": success,
        "failed": failed,
        "success_rate_pct": None if requests_total == 0 else success / requests_total * 100,
        "error_rate_pct": None if requests_total == 0 else failed / requests_total * 100,
        "median_ms": None if not all_durations else median(all_durations),
        "p95_ms": None if not all_durations else percentile(all_durations, 95),
        "min_ms": None if not all_durations else min(all_durations),
        "max_ms": None if not all_durations else max(all_durations),
        "recovery_min_s": None if not recovery_values else min(recovery_values),
        "recovery_median_s": None if not recovery_values else median(recovery_values),
        "recovery_mean_s": None if not recovery_values else mean(recovery_values),
        "recovery_max_s": None if not recovery_values else max(recovery_values),
        "runs_excluded": ",".join(sorted(EXCLUDE_FROM_REGULAR_EVALUATION)),
    }

    fields = list(aggregate.keys())

    with OUT_AGG.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        out = dict(aggregate)
        for key, value in list(out.items()):
            if isinstance(value, float):
                out[key] = f"{value:.2f}"
        writer.writerow(out)


def main():
    rows = []
    for run_dir in sorted(BASE.glob("run-*")):
        if not run_dir.is_dir():
            continue
        row = parse_run(run_dir)
        if row:
            rows.append(row)

    write_detail(rows)
    write_aggregate(rows)

    print(f"Wrote {OUT_DETAIL} with {len(rows)} rows")
    print(f"Wrote {OUT_AGG}")


if __name__ == "__main__":
    main()
