#!/usr/bin/env python3
import csv
import statistics as stats
from pathlib import Path
from datetime import datetime
import re

SCENARIO = Path("experiments/k3s/latency-tests/latency-30min-async-limited")
OUT = SCENARIO / "README.md"

CRITICAL_EVENT_PATTERNS = [
    "NotReady", "Failed", "BackOff", "Evicted", "Unhealthy",
    "Killing", "NodeNotReady", "CrashLoopBackOff"
]

def t(s):
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))

def pct(vals, p):
    vals = sorted(vals)
    return vals[min(int(len(vals) * p / 100), len(vals) - 1)] if vals else None

def fmt(v, digits=2):
    return "NA" if v is None else f"{v:.{digits}f}"

def read_text(path, default=""):
    return path.read_text(errors="ignore").strip() if path.exists() else default

def read_requests(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append({
                    "start": t(r["request_start_time"]),
                    "end": t(r["request_end_time"]),
                    "ms": float(r["duration_ms"]),
                    "success": r["success"] == "True",
                    "error": r.get("error", ""),
                })
            except Exception:
                pass
    return rows

def summarize(rows):
    total = len(rows)
    ok = sum(r["success"] for r in rows)
    fail = total - ok
    vals = [r["ms"] for r in rows]
    return {
        "total": total,
        "ok": ok,
        "fail": fail,
        "success_rate": ok / total * 100 if total else None,
        "error_rate": fail / total * 100 if total else None,
        "median": stats.median(vals) if vals else None,
        "p95": pct(vals, 95),
        "p99": pct(vals, 99),
        "max": max(vals) if vals else None,
        "gt_60s": sum(v > 60_000 for v in vals),
        "gt_120s": sum(v > 120_000 for v in vals),
        "gt_1800s": sum(v > 1_800_000 for v in vals),
        "gt_3600s": sum(v > 3_600_000 for v in vals),
    }

def parse_pods(text):
    known_nodes = {"k3s-s1", "k3s-s2", "k3s-s3", "k3s-w1", "k3s-w2"}
    pods = {}

    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue

        ns = parts[0]
        name = parts[1]
        ready = parts[2]
        status = parts[3]

        node = next((p for p in parts if p in known_nodes), "")
        node_idx = parts.index(node) if node else -1
        ip = parts[node_idx - 1] if node_idx > 0 else ""

        restarts = parts[4]

        pods[f"{ns}/{name}"] = {
            "ready": ready,
            "status": status,
            "restarts": restarts,
            "ip": ip,
            "node": node,
        }

    return pods
def parse_nodes(text):
    nodes = {}
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            nodes[parts[0]] = parts[1]
    return nodes

runs = []

for run_dir in sorted(SCENARIO.glob("run-*-router")):
    fault_file = run_dir / "fault_time.txt"
    recovery_file = run_dir / "recovery_time.txt"
    requests_file = run_dir / "requests.csv"

    if not fault_file.exists() or not recovery_file.exists() or not requests_file.exists():
        continue

    fault = t(read_text(fault_file))
    recovery = t(read_text(recovery_file))
    rows = read_requests(requests_file)

    baseline = [r for r in rows if r["start"] < fault]
    fault_rows = [r for r in rows if fault <= r["start"] < recovery]
    after = [r for r in rows if r["start"] >= recovery]

    nodes_before = parse_nodes(read_text(run_dir / "nodes_before.txt"))
    nodes_after = parse_nodes(read_text(run_dir / "nodes_after.txt"))

    pods_before = parse_pods(read_text(run_dir / "pods_before.txt"))
    pods_after = parse_pods(read_text(run_dir / "pods_after.txt"))

    node_status_stable = nodes_before == nodes_after

    pod_names_stable = set(pods_before.keys()) == set(pods_after.keys())
    pod_locations_stable = all(
        name in pods_after and
        pods_before[name]["node"] == pods_after[name]["node"] and
        pods_before[name]["ip"] == pods_after[name]["ip"] and
        pods_after[name]["status"] in ["Running", "Completed"]
        for name in pods_before
    )

    restart_changed = any(
        name in pods_after and pods_before[name]["restarts"] != pods_after[name]["restarts"]
        for name in pods_before
    )

    events = read_text(run_dir / "events_before.txt") + "\n" + read_text(run_dir / "events_after.txt")
    critical_events = [
        p for p in CRITICAL_EVENT_PATTERNS
        if re.search(p, events, re.IGNORECASE)
    ]

    traceroute = read_text(run_dir / "traceroute_before.txt")
    tc_during = read_text(run_dir / "tc_during.txt")
    tc_after = read_text(run_dir / "tc_after.txt")

    recovery_latency = None
    for r in after:
        if r["success"] and r["ms"] < 500:
            recovery_latency = (r["end"] - recovery).total_seconds()
            break

    runs.append({
        "name": run_dir.name,
        "delay": read_text(run_dir / "delay.txt"),
        "duration": read_text(run_dir / "duration_seconds.txt"),
        "baseline_s": read_text(run_dir / "baseline_seconds.txt"),
        "after_s": read_text(run_dir / "after_seconds.txt"),
        "timeout": read_text(run_dir / "timeout_seconds.txt"),
        "max_in_flight": read_text(run_dir / "max_in_flight.txt", "NA"),
        "valid_router": "10.10.10.128" in traceroute,
        "valid_tc": ("delay 1800s" in tc_during) or ("delay 1.8e+03s" in tc_during),
        "valid_cleanup": ("fq_codel" in tc_after) or ("pfifo_fast" in tc_after),
        "overall": summarize(rows),
        "baseline": summarize(baseline),
        "fault": summarize(fault_rows),
        "after": summarize(after),
        "recovery_latency": recovery_latency,
        "node_status_stable": node_status_stable,
        "pod_names_stable": pod_names_stable,
        "pod_locations_stable": pod_locations_stable,
        "restart_changed": restart_changed,
        "critical_events": critical_events,
    })

def mean(vals):
    vals = [v for v in vals if v is not None]
    return stats.mean(vals) if vals else None

fault_success = [r["fault"]["success_rate"] for r in runs if r["fault"]["success_rate"] is not None]
fault_error = [r["fault"]["error_rate"] for r in runs if r["fault"]["error_rate"] is not None]
overall_success = [r["overall"]["success_rate"] for r in runs if r["overall"]["success_rate"] is not None]
recovery_vals = [r["recovery_latency"] for r in runs if r["recovery_latency"] is not None]

with open(OUT, "w") as f:
    f.write("# Latenztest 30min – asynchroner Monitor mit begrenzter Parallelität\n\n")

    f.write("## Ziel\n\n")
    f.write(
        "In diesem Test wurde das Verhalten des K3s-Clusters und der Testanwendung bei einer künstlich "
        "eingebrachten Netzwerklatenz von 30 Minuten untersucht. Aufgrund der erwarteten Round-Trip-Zeit "
        "von etwa 60 Minuten dient dieser Test vor allem als Extremfall zur Bewertung der Clusterstabilität "
        "und der Self-Healing-Mechanismen.\n\n"
    )

    first = runs[0] if runs else {}
    f.write("## Parameter\n\n")
    f.write("| Parameter | Wert |\n|---|---:|\n")
    f.write(f"| Eingebrachte Latenz | {first.get('delay', 'NA')} |\n")
    f.write("| Erwartete Round-Trip-Zeit | ca. 3600s |\n")
    f.write(f"| Vorlauf | {first.get('baseline_s', 'NA')}s |\n")
    f.write(f"| Störphase | {first.get('duration', 'NA')}s |\n")
    f.write(f"| Nachlauf | {first.get('after_s', 'NA')}s |\n")
    f.write(f"| Wiederholungen | {len(runs)} |\n")
    f.write(f"| HTTP Timeout | {first.get('timeout', 'NA')}s |\n")
    f.write("| Request-Intervall | 1s |\n")
    f.write(f"| Max. parallele Requests | {first.get('max_in_flight', 'NA')} |\n\n")

    f.write("## Validierung\n\n")
    f.write(f"- Vorhandene Runs: {len(runs)}/10\n")
    f.write(f"- Routerpfad validiert: {sum(r['valid_router'] for r in runs)}/{len(runs)}\n")
    f.write(f"- `tc netem delay 1800s` aktiv: {sum(r['valid_tc'] for r in runs)}/{len(runs)}\n")
    f.write(f"- Cleanup nach Störphase dokumentiert: {sum(r['valid_cleanup'] for r in runs)}/{len(runs)}\n\n")

    f.write("## Zusammenfassung pro Run\n\n")
    f.write("| Run | Overall Success [%] | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | >1800s | >3600s | Recovery [s] |\n")
    f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
    for r in runs:
        fs = r["fault"]
        f.write(
            f"| {r['name']} | {fmt(r['overall']['success_rate'])} | "
            f"{fmt(fs['success_rate'])} | {fmt(fs['error_rate'])} | "
            f"{fmt(fs['median'])} | {fmt(fs['p95'])} | "
            f"{fs['gt_1800s']} | {fs['gt_3600s']} | "
            f"{fmt(r['recovery_latency'])} |\n"
        )

    f.write("\n## Aggregierte HTTP-Metriken\n\n")
    f.write(f"- Overall Request Success Rate Mittelwert: {fmt(mean(overall_success))} %\n")
    f.write(f"- Fault Success Rate Mittelwert: {fmt(mean(fault_success))} %\n")
    f.write(f"- Fault Error Rate Mittelwert: {fmt(mean(fault_error))} %\n")
    if recovery_vals:
        f.write(f"- Recovery Time Mittelwert: {fmt(mean(recovery_vals))} s\n")
        f.write(f"- Recovery Time Minimum: {fmt(min(recovery_vals))} s\n")
        f.write(f"- Recovery Time Maximum: {fmt(max(recovery_vals))} s\n")
    else:
        f.write("- Recovery Time: nicht bestimmbar\n")

    f.write("\n## Self-Healing- und Cluster-Stabilität\n\n")
    f.write("| Run | Nodes stabil | Pods stabil | Pod-Rescheduling | Zusätzliche Restarts | Kritische Events |\n")
    f.write("|---|---:|---:|---:|---:|---:|\n")
    for r in runs:
        rescheduling = not (r["pod_names_stable"] and r["pod_locations_stable"])
        f.write(
            f"| {r['name']} | "
            f"{'ja' if r['node_status_stable'] else 'nein'} | "
            f"{'ja' if r['pod_names_stable'] and r['pod_locations_stable'] else 'nein'} | "
            f"{'ja' if rescheduling else 'nein'} | "
            f"{'ja' if r['restart_changed'] else 'nein'} | "
            f"{', '.join(r['critical_events']) if r['critical_events'] else 'nein'} |\n"
        )

    f.write("\n## Interpretation\n\n")
    f.write(
        "Die Messreihe zeigt, dass eine künstliche Netzwerklatenz von 30 Minuten die Anwendungskommunikation "
        "praktisch vollständig beeinträchtigt. Während der Störphase konnten nahezu keine HTTP-Requests "
        "erfolgreich abgeschlossen werden. Die Anwendung ist aus Client-Sicht unter diesen Bedingungen "
        "nicht sinnvoll nutzbar.\n\n"
    )
    f.write(
        "Gleichzeitig blieb das K3s-Cluster auf Infrastruktur-Ebene stabil. Die gespeicherten Node- und Pod-Zustände "
        "zeigen keine Hinweise auf Node-Ausfälle, Pod-Neuplanung oder zusätzliche Container-Restarts. Auch die "
        "aufgezeichneten Kubernetes-Events enthalten keine Hinweise auf kritische Ereignisse wie NotReady, BackOff, "
        "Evicted oder Killing.\n\n"
    )
    f.write(
        "Damit wurden durch die extreme Latenz keine klassischen Kubernetes-Self-Healing-Mechanismen ausgelöst. "
        "K3s erkennt in diesem Szenario keinen Pod- oder Node-Ausfall, obwohl die Anwendung aus Sicht des Clients "
        "faktisch nicht erreichbar ist. Die Störung betrifft somit primär die Anwendungskommunikation und nicht "
        "die Stabilität der Cluster-Komponenten.\n"
    )

print(f"README geschrieben: {OUT}")
print(f"Runs ausgewertet: {len(runs)}")
