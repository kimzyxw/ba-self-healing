#!/usr/bin/env python3
from pathlib import Path
import argparse
import csv
import re
import statistics as stats


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a latency comparison summary across latency scenarios."
    )
    parser.add_argument(
        "--system",
        required=True,
        choices=["k3s", "kubeedge"],
        help="System name used under experiments/<system>/latency-tests",
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Optional explicit latency-tests directory",
    )
    return parser.parse_args()


def parse_summary(path):
    sections = {"global": {}}
    current = "global"

    if not path.exists():
        return sections

    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue

        m = re.match(r"--- (.+) ---", line)
        if m:
            current = m.group(1).strip()
            sections[current] = {}
            continue

        if "=" in line:
            k, v = line.split("=", 1)
            sections.setdefault(current, {})[k.strip()] = v.strip()

    return sections


def num(x):
    if x is None or str(x).strip() in ("", "NA", "None"):
        return None
    x = str(x).replace("%", "").strip()
    try:
        return float(x)
    except ValueError:
        return None


def read_lines(path):
    if not path.exists():
        return []
    return path.read_text(errors="replace").splitlines()


def parse_testapp_pods(path):
    pods = {}

    for line in read_lines(path):
        line = line.strip()
        if not line or line.startswith("NAMESPACE") or line.startswith("NAME"):
            continue

        parts = line.split()
        if len(parts) < 5:
            continue

        if parts[0] == "testapp" and "nginx-testapp" in parts[1]:
            restart_raw = parts[4]
            restart_match = re.match(r"(\d+)", restart_raw)
            restarts = int(restart_match.group(1)) if restart_match else 0

            pods[parts[1]] = {
                "name": parts[1],
                "ready": parts[2],
                "status": parts[3],
                "restarts": restarts,
                "node": parts[7] if len(parts) > 7 else "",
            }

    return pods


def parse_nodes(path):
    nodes = {}

    for line in read_lines(path):
        line = line.strip()
        if not line or line.startswith("NAME"):
            continue

        parts = line.split()
        if len(parts) >= 2:
            nodes[parts[0]] = parts[1]

    return nodes


def count_event_patterns(path):
    text = "\n".join(read_lines(path))
    return {
        "node_notready_event_lines": text.count("NodeNotReady"),
        "node_ready_event_lines": text.count("NodeReady"),
        "taintmanager_marking_lines": text.count("Marking for deletion"),
        "taintmanager_cancel_lines": text.count("Cancelling deletion"),
        "unreachable_lines": text.count("Unreachable"),
    }


def median(vals):
    vals = [v for v in vals if v is not None]
    return stats.median(vals) if vals else None


def mean(vals):
    vals = [v for v in vals if v is not None]
    return stats.mean(vals) if vals else None


def fmt(v, digits=2):
    if v is None:
        return "NA"
    return f"{v:.{digits}f}"


def main():
    args = parse_args()

    base = Path(args.base_dir) if args.base_dir else Path("experiments") / args.system / "latency-tests"

    scenarios = [
        ("latency-1s-async-limited", "1s"),
        ("latency-1min-async-limited", "1min"),
        ("latency-10min-async-limited", "10min"),
        ("latency-30min-async-limited", "30min"),
    ]

    out_csv = base / f"{args.system}-latency-comparison-summary.csv"
    out_txt = base / f"{args.system}-latency-comparison-summary.txt"

    scenario_rows = []

    for scenario_name, label in scenarios:
        scenario = base / scenario_name
        run_rows = []

        for run_dir in sorted(scenario.glob("run-*-router")):
            summary = parse_summary(run_dir / "summary.txt")

            pods_before = parse_testapp_pods(run_dir / "pods_before.txt")
            pods_after = parse_testapp_pods(run_dir / "pods_after.txt")
            nodes_after = parse_nodes(run_dir / "nodes_after.txt")

            before_names = set(pods_before)
            after_names = set(pods_after)

            all_testapp_after_running = (
                len(pods_after) == 3
                and all(p["status"] == "Running" for p in pods_after.values())
                and all(p["ready"] == "1/1" for p in pods_after.values())
            )

            all_nodes_after_ready = (
                bool(nodes_after)
                and all("Ready" in status and "NotReady" not in status for status in nodes_after.values())
            )

            event_counts = count_event_patterns(run_dir / "events_after.txt")

            container_restart_delta = (
                sum(p["restarts"] for p in pods_after.values())
                - sum(p["restarts"] for p in pods_before.values())
            )

            row = {
                "scenario": scenario_name,
                "label": label,
                "run": run_dir.name.replace("-router", ""),

                "delay": summary.get("global", {}).get("delay"),
                "router_ifaces": summary.get("global", {}).get("router_ifaces"),
                "tc_active": summary.get("validation", {}).get("tc_active"),
                "tc_cleanup_documented": summary.get("validation", {}).get("tc_cleanup_documented"),
                "latency_applied": summary.get("validation", {}).get("latency_applied"),

                "overall_success_rate": num(summary.get("overall", {}).get("success_rate")),
                "overall_error_rate": num(summary.get("overall", {}).get("error_rate")),
                "baseline_success_rate": num(summary.get("baseline", {}).get("success_rate")),
                "baseline_error_rate": num(summary.get("baseline", {}).get("error_rate")),
                "fault_success_rate": num(summary.get("fault", {}).get("success_rate")),
                "fault_error_rate": num(summary.get("fault", {}).get("error_rate")),
                "after_success_rate": num(summary.get("after", {}).get("success_rate")),
                "after_error_rate": num(summary.get("after", {}).get("error_rate")),

                "baseline_median_ms": num(summary.get("baseline", {}).get("median_ms")),
                "fault_median_ms": num(summary.get("fault", {}).get("median_ms")),
                "fault_p95_ms": num(summary.get("fault", {}).get("p95_ms")),
                "fault_p99_ms": num(summary.get("fault", {}).get("p99_ms")),
                "after_median_ms": num(summary.get("after", {}).get("median_ms")),
                "recovery_latency_s": num(summary.get("recovery", {}).get("recovery_latency_s")),
                "after_requests": num(summary.get("after", {}).get("requests_total")),

                "pod_names_changed": before_names != after_names,
                "removed_testapp_pods": len(before_names - after_names),
                "new_testapp_pods": len(after_names - before_names),
                "container_restart_delta": container_restart_delta,

                "testapp_after_running": all_testapp_after_running,
                "all_nodes_after_ready": all_nodes_after_ready,
                "stable_after_snapshot": all_testapp_after_running and all_nodes_after_ready,

                **event_counts,
            }

            run_rows.append(row)

        if not run_rows:
            continue

        comparison_row = {
            "scenario": scenario_name,
            "label": label,
            "runs": len(run_rows),

            "delay_values": "|".join(sorted(set(str(r["delay"]) for r in run_rows))),
            "router_ifaces_values": "|".join(sorted(set(str(r["router_ifaces"]) for r in run_rows))),
            "tc_active_values": "|".join(sorted(set(str(r["tc_active"]) for r in run_rows))),
            "latency_applied_values": "|".join(sorted(set(str(r["latency_applied"]) for r in run_rows))),

            "overall_success_rate_median": median([r["overall_success_rate"] for r in run_rows]),
            "overall_error_rate_median": median([r["overall_error_rate"] for r in run_rows]),
            "baseline_success_rate_median": median([r["baseline_success_rate"] for r in run_rows]),
            "fault_success_rate_median": median([r["fault_success_rate"] for r in run_rows]),
            "fault_error_rate_median": median([r["fault_error_rate"] for r in run_rows]),
            "after_success_rate_median": median([r["after_success_rate"] for r in run_rows]),
            "after_error_rate_median": median([r["after_error_rate"] for r in run_rows]),

            "baseline_median_ms_median": median([r["baseline_median_ms"] for r in run_rows]),
            "fault_median_ms_median": median([r["fault_median_ms"] for r in run_rows]),
            "fault_p95_ms_median": median([r["fault_p95_ms"] for r in run_rows]),
            "fault_p99_ms_median": median([r["fault_p99_ms"] for r in run_rows]),
            "after_median_ms_median": median([r["after_median_ms"] for r in run_rows]),

            "recovery_latency_s_median": median([r["recovery_latency_s"] for r in run_rows]),
            "recovery_latency_s_mean": mean([r["recovery_latency_s"] for r in run_rows]),
            "recovery_latency_s_max": max(
                [r["recovery_latency_s"] for r in run_rows if r["recovery_latency_s"] is not None],
                default=None,
            ),

            "after_requests_median": median([r["after_requests"] for r in run_rows]),
            "runs_with_after_requests_0": sum(1 for r in run_rows if r["after_requests"] == 0),

            "runs_with_pod_name_changes": sum(1 for r in run_rows if r["pod_names_changed"]),
            "removed_testapp_pods_median": median([r["removed_testapp_pods"] for r in run_rows]),
            "new_testapp_pods_median": median([r["new_testapp_pods"] for r in run_rows]),
            "container_restart_delta_median": median([r["container_restart_delta"] for r in run_rows]),

            "runs_with_testapp_after_running": sum(1 for r in run_rows if r["testapp_after_running"]),
            "runs_with_all_nodes_after_ready": sum(1 for r in run_rows if r["all_nodes_after_ready"]),
            "runs_with_stable_after_snapshot": sum(1 for r in run_rows if r["stable_after_snapshot"]),

            "node_notready_event_lines_median": median([r["node_notready_event_lines"] for r in run_rows]),
            "taintmanager_marking_lines_median": median([r["taintmanager_marking_lines"] for r in run_rows]),
            "taintmanager_cancel_lines_median": median([r["taintmanager_cancel_lines"] for r in run_rows]),
        }

        scenario_rows.append(comparison_row)

    if not scenario_rows:
        raise SystemExit(f"No scenario data found under {base}")

    fields = list(scenario_rows[0].keys())

    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(scenario_rows)

    lines = []
    lines.append(f"# {args.system} Latency Comparison Summary")
    lines.append("")
    lines.append("## Vergleichstabelle")
    lines.append("")
    lines.append("| Szenario | Runs | Fault Success Median [%] | Fault Error Median [%] | After Success Median [%] | Recovery Median [s] | Pod-Ersetzungen Runs | Stable After Snapshot | NodeNotReady Events Median |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    for r in scenario_rows:
        lines.append(
            f"| {r['label']} "
            f"| {r['runs']} "
            f"| {fmt(r['fault_success_rate_median'])} "
            f"| {fmt(r['fault_error_rate_median'])} "
            f"| {fmt(r['after_success_rate_median'])} "
            f"| {fmt(r['recovery_latency_s_median'])} "
            f"| {r['runs_with_pod_name_changes']}/{r['runs']} "
            f"| {r['runs_with_stable_after_snapshot']}/{r['runs']} "
            f"| {fmt(r['node_notready_event_lines_median'])} |"
        )

    lines.append("")
    lines.append("## Detailvergleich")
    lines.append("")

    for r in scenario_rows:
        lines.append(f"### {r['label']} ({r['scenario']})")
        lines.append("")
        lines.append(f"- Runs: {r['runs']}")
        lines.append(f"- Delay-Werte: {r['delay_values']}")
        lines.append(f"- Router-Interfaces: {r['router_ifaces_values']}")
        lines.append(f"- tc_active-Werte: {r['tc_active_values']}")
        lines.append(f"- latency_applied-Werte: {r['latency_applied_values']}")
        lines.append(f"- Baseline Success Rate Median: {fmt(r['baseline_success_rate_median'])} %")
        lines.append(f"- Fault Success Rate Median: {fmt(r['fault_success_rate_median'])} %")
        lines.append(f"- Fault Error Rate Median: {fmt(r['fault_error_rate_median'])} %")
        lines.append(f"- After Success Rate Median: {fmt(r['after_success_rate_median'])} %")
        lines.append(f"- After Error Rate Median: {fmt(r['after_error_rate_median'])} %")
        lines.append(f"- Fault Median Latency Median: {fmt(r['fault_median_ms_median'])} ms")
        lines.append(f"- Fault p95 Latency Median: {fmt(r['fault_p95_ms_median'])} ms")
        lines.append(f"- After Median Latency Median: {fmt(r['after_median_ms_median'])} ms")
        lines.append(f"- Recovery Latency Median: {fmt(r['recovery_latency_s_median'])} s")
        lines.append(f"- Recovery Latency Mean: {fmt(r['recovery_latency_s_mean'])} s")
        lines.append(f"- Recovery Latency Max: {fmt(r['recovery_latency_s_max'])} s")
        lines.append(f"- Runs mit after_requests=0: {r['runs_with_after_requests_0']}/{r['runs']}")
        lines.append(f"- Runs mit Pod-Ersetzungen: {r['runs_with_pod_name_changes']}/{r['runs']}")
        lines.append(f"- Container-Restart-Delta Median: {fmt(r['container_restart_delta_median'])}")
        lines.append(f"- Runs mit stabilen Testapp-Pods im After-Snapshot: {r['runs_with_testapp_after_running']}/{r['runs']}")
        lines.append(f"- Runs mit allen Nodes Ready im After-Snapshot: {r['runs_with_all_nodes_after_ready']}/{r['runs']}")
        lines.append(f"- Runs mit stabilem After-Snapshot: {r['runs_with_stable_after_snapshot']}/{r['runs']}")
        lines.append(f"- NodeNotReady-Event-Lines Median: {fmt(r['node_notready_event_lines_median'])}")
        lines.append(f"- TaintManager Marking Lines Median: {fmt(r['taintmanager_marking_lines_median'])}")
        lines.append("")

    lines.append("## Hinweis")
    lines.append("")
    lines.append("Bei sehr großen Latenzwerten kann `tc` Werte in wissenschaftlicher Notation ausgeben, z. B. `1.8e+03s` statt `1800s`. Falls `tc_active=no` erscheint, obwohl `tc_during.txt` eine passende aktive netem-Regel zeigt und `latency_applied=yes` gesetzt ist, wird dies als Parsing-Artefakt der Validierung bewertet.")
    lines.append("")

    out_txt.write_text("\n".join(lines))

    print(out_txt.read_text())
    print(f"\nCSV written to: {out_csv}")
    print(f"TXT written to: {out_txt}")


if __name__ == "__main__":
    main()
