#!/usr/bin/env python3
from pathlib import Path
import argparse
import csv
import re
import statistics as stats


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_dir", help="Path to packet-loss scenario directory")
    return parser.parse_args()


def pct_to_float(v):
    if not v or v == "NA":
        return None
    return float(v.replace("%", ""))


def num(v):
    if not v or v == "NA":
        return None
    return float(v)


def med(values):
    vals = [v for v in values if v is not None]
    return stats.median(vals) if vals else None


def mean(values):
    vals = [v for v in values if v is not None]
    return stats.mean(vals) if vals else None


def fmt(v):
    return f"{v:.2f}" if v is not None else "NA"


def parse_summary(path: Path):
    text = path.read_text()
    data = {"run": path.parent.name}

    for key in [
        "loss", "duration_s", "baseline_s", "after_s",
        "timeout_s", "max_in_flight", "router_iface",
    ]:
        m = re.search(rf"^{key}=(.*)$", text, re.M)
        data[key] = m.group(1).strip() if m else ""

    for key in ["router_path_valid", "packet_loss_applied", "tc_cleanup_documented"]:
        m = re.search(rf"^{key}=(.*)$", text, re.M)
        data[key] = m.group(1).strip() if m else ""

    m = re.search(r"^recovery_latency_s=(.*)$", text, re.M)
    data["recovery_latency_s"] = m.group(1).strip() if m else "NA"

    sections = {}
    current = None

    for line in text.splitlines():
        sec = re.match(r"--- (overall|baseline|fault|after) ---", line)
        if sec:
            current = sec.group(1)
            sections[current] = {}
            continue

        if current and "=" in line:
            k, v = line.split("=", 1)
            sections[current][k.strip()] = v.strip()

    keys = [
        "requests_total", "success", "failed", "success_rate", "error_rate",
        "avg_ms", "median_ms", "p95_ms", "p99_ms", "min_ms", "max_ms",
        "success_median_ms", "success_p95_ms", "fail_median_ms",
        "errors", "timeouts",
    ]

    for sec in ["overall", "baseline", "fault", "after"]:
        s = sections.get(sec, {})
        for key in keys:
            data[f"{sec}_{key}"] = s.get(key, "")

    pre = path.parent / "after_preflight_status.txt"
    data["after_preflight_ok"] = pre.read_text().strip().split("=")[-1] if pre.exists() else "NA"

    return data


def main():
    args = parse_args()
    base = Path(args.scenario_dir)
    scenario = base.name

    runs = []
    for d in sorted(base.glob("run-*-router")):
        s = d / "summary.txt"
        if s.exists():
            runs.append(parse_summary(s))

    if not runs:
        raise SystemExit(f"No run summaries found in {base}")

    out_csv = base / "packet-loss-summary.csv"
    fields = [
        "run", "loss", "duration_s", "baseline_s", "after_s",
        "timeout_s", "max_in_flight", "router_iface",
        "router_path_valid", "packet_loss_applied", "tc_cleanup_documented",
        "after_preflight_ok",
        "overall_requests_total", "overall_success_rate", "overall_error_rate",
        "overall_median_ms", "overall_p95_ms", "overall_p99_ms", "overall_timeouts",
        "baseline_requests_total", "baseline_success_rate", "baseline_median_ms",
        "fault_requests_total", "fault_success_rate", "fault_error_rate",
        "fault_median_ms", "fault_p95_ms", "fault_p99_ms", "fault_max_ms",
        "fault_timeouts", "fault_errors",
        "after_requests_total", "after_success_rate", "after_error_rate",
        "after_median_ms",
        "recovery_latency_s",
    ]

    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in runs:
            writer.writerow({k: r.get(k, "") for k in fields})

    lines = []
    lines.append(f"scenario={scenario}")
    lines.append(f"runs={len(runs)}")
    lines.append(f"router_path_valid={sum(r.get('router_path_valid') == 'yes' for r in runs)}/{len(runs)}")
    lines.append(f"packet_loss_applied={sum(r.get('packet_loss_applied') == 'yes' for r in runs)}/{len(runs)}")
    lines.append(f"tc_cleanup_documented={sum(r.get('tc_cleanup_documented') == 'yes' for r in runs)}/{len(runs)}")
    lines.append(f"after_preflight_ok={sum(r.get('after_preflight_ok') == 'yes' for r in runs)}/{len(runs)}")

    if runs:
        lines.append(f"loss={runs[0].get('loss', '')}")
        lines.append(f"duration_s={runs[0].get('duration_s', '')}")
        lines.append(f"baseline_s={runs[0].get('baseline_s', '')}")
        lines.append(f"after_s={runs[0].get('after_s', '')}")
        lines.append(f"timeout_s={runs[0].get('timeout_s', '')}")
        lines.append(f"max_in_flight={runs[0].get('max_in_flight', '')}")
        lines.append(f"router_iface={runs[0].get('router_iface', '')}")

    for phase in ["overall", "baseline", "fault", "after"]:
        lines.append("")
        lines.append(f"[{phase}]")
        lines.append(f"{phase}_success_rate_percent_median={fmt(med([pct_to_float(r.get(f'{phase}_success_rate')) for r in runs]))}")
        lines.append(f"{phase}_success_rate_percent_mean={fmt(mean([pct_to_float(r.get(f'{phase}_success_rate')) for r in runs]))}")
        lines.append(f"{phase}_error_rate_percent_median={fmt(med([pct_to_float(r.get(f'{phase}_error_rate')) for r in runs]))}")
        lines.append(f"{phase}_error_rate_percent_mean={fmt(mean([pct_to_float(r.get(f'{phase}_error_rate')) for r in runs]))}")
        lines.append(f"{phase}_median_ms_median={fmt(med([num(r.get(f'{phase}_median_ms')) for r in runs]))}")
        lines.append(f"{phase}_p95_ms_median={fmt(med([num(r.get(f'{phase}_p95_ms')) for r in runs]))}")
        lines.append(f"{phase}_p99_ms_median={fmt(med([num(r.get(f'{phase}_p99_ms')) for r in runs]))}")
        lines.append(f"{phase}_max_ms_median={fmt(med([num(r.get(f'{phase}_max_ms')) for r in runs]))}")
        lines.append(f"{phase}_timeouts_total={sum(int(float(r.get(f'{phase}_timeouts') or 0)) for r in runs)}")

    rec_vals = [num(r.get("recovery_latency_s")) for r in runs]
    rec_vals = [v for v in rec_vals if v is not None]

    lines.append("")
    lines.append("[recovery]")
    lines.append(f"recovery_latency_s_min={fmt(min(rec_vals) if rec_vals else None)}")
    lines.append(f"recovery_latency_s_median={fmt(stats.median(rec_vals) if rec_vals else None)}")
    lines.append(f"recovery_latency_s_mean={fmt(stats.mean(rec_vals) if rec_vals else None)}")
    lines.append(f"recovery_latency_s_max={fmt(max(rec_vals) if rec_vals else None)}")

    out_agg = base / "packet-loss-summary-aggregate.txt"
    out_agg.write_text("\n".join(lines) + "\n")

    print(f"Wrote {out_csv}")
    print(f"Wrote {out_agg}")
    print(f"Runs ausgewertet: {len(runs)}")


if __name__ == "__main__":
    main()
