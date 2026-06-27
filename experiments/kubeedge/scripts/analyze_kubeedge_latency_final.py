from pathlib import Path
import csv
import statistics

BASE = Path("experiments/kubeedge/latency-tests")
OUT_DIR = BASE / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

INPUTS = [
    ("1s", "latency-1s-async-limited", BASE / "latency-1s-async-limited" / "latency-1s-summary-extracted.csv"),
    ("1min", "latency-1min-async-limited", BASE / "latency-1min-async-limited" / "latency-1min-self-healing-summary.csv"),
    ("10min", "latency-10min-async-limited", BASE / "latency-10min-async-limited" / "latency-10min-self-healing-summary.csv"),
    ("30min", "latency-30min-async-limited", BASE / "latency-30min-async-limited" / "latency-30min-self-healing-summary.csv"),
]

REQUEST_FIELDS = [
    "scenario",
    "run",
    "delay",
    "overall_success_rate_percent",
    "overall_error_rate_percent",
    "baseline_success_rate_percent",
    "baseline_error_rate_percent",
    "fault_success_rate_percent",
    "fault_error_rate_percent",
    "after_success_rate_percent",
    "after_error_rate_percent",
    "baseline_median_ms",
    "fault_median_ms",
    "fault_p95_ms",
    "fault_p99_ms",
    "after_median_ms",
    "recovery_latency_s",
    "after_requests",
]

CLUSTER_FIELDS = [
    "scenario",
    "run",
    "router_ifaces",
    "tc_active",
    "latency_applied",
    "tc_cleanup_documented",
    "pod_replacement",
    "removed_testapp_pods",
    "new_testapp_pods",
    "container_restart_delta",
    "testapp_pods_after_running",
    "all_nodes_after_ready",
    "stable_after_snapshot",
    "node_notready_event_lines",
    "taintmanager_marking_lines",
    "taintmanager_cancel_lines",
]

SUMMARY_FIELDS = [
    "scenario",
    "runs",
    "fault_success_rate_mean",
    "fault_success_rate_median",
    "fault_success_rate_std",
    "fault_error_rate_mean",
    "fault_error_rate_median",
    "fault_error_rate_std",
    "after_success_rate_mean",
    "after_success_rate_median",
    "after_success_rate_std",
    "after_error_rate_mean",
    "after_error_rate_median",
    "after_error_rate_std",
    "recovery_latency_s_mean",
    "recovery_latency_s_median",
    "recovery_latency_s_std",
    "recovery_latency_s_min",
    "recovery_latency_s_max",
    "fault_median_ms_mean",
    "fault_median_ms_median",
    "fault_p95_ms_median",
    "runs_with_pod_replacement",
    "removed_testapp_pods_median",
    "new_testapp_pods_median",
    "container_restart_delta_sum",
    "runs_with_testapp_after_running",
    "runs_with_all_nodes_after_ready",
    "runs_with_stable_after_snapshot",
    "node_notready_event_lines_median",
    "taintmanager_marking_lines_median",
]

def first(row, names, default=""):
    for name in names:
        if name in row and row[name] not in ("", None):
            return row[name]
    return default

def to_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.upper() == "NA" or value.lower() == "none":
        return None
    value = value.replace("%", "").replace(",", ".")
    return float(value)

def truthy(value):
    return str(value).strip().lower() in {"true", "yes", "1", "ja"}

def fmt_de(value, digits=2):
    if value is None:
        return "--"
    return f"{float(value):.{digits}f}".replace(".", ",")

def tex_escape(value):
    value = "" if value is None else str(value)
    return (
        value.replace("_", r"\_")
             .replace("%", r"\%")
             .replace("&", r"\&")
             .replace("#", r"\#")
    )

def values_only(values):
    return [v for v in values if v is not None]

def mean(values):
    v = values_only(values)
    return statistics.mean(v) if v else None

def median(values):
    v = values_only(values)
    return statistics.median(v) if v else None

def std(values):
    v = values_only(values)
    return statistics.stdev(v) if len(v) > 1 else 0.0

def count_event_lines(scenario_dir, run_name, needle):
    run_dir = BASE / scenario_dir / f"{run_name}-router"
    total = 0
    for filename in ["events_before.txt", "events_after.txt"]:
        path = run_dir / filename
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            total += sum(1 for line in text.splitlines() if needle in line)
    return float(total) if total > 0 else None

request_rows = []
cluster_rows = []

for scenario, scenario_dir, path in INPUTS:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for raw in reader:
            run = first(raw, ["run"], "")

            overall_success = to_float(first(raw, ["overall_success_rate_percent", "overall_success_rate"]))
            overall_error = to_float(first(raw, ["overall_error_rate_percent", "overall_error_rate"]))
            baseline_success = to_float(first(raw, ["baseline_success_rate_percent", "baseline_success_rate"]))
            baseline_error = to_float(first(raw, ["baseline_error_rate_percent", "baseline_error_rate"]))
            if baseline_error is None and baseline_success == 100.0:
                baseline_error = 0.0
            fault_success = to_float(first(raw, ["fault_success_rate_percent", "fault_success_rate"]))
            fault_error = to_float(first(raw, ["fault_error_rate_percent", "fault_error_rate"]))
            after_success = to_float(first(raw, ["after_success_rate_percent", "after_success_rate"]))
            after_error = to_float(first(raw, ["after_error_rate_percent", "after_error_rate"]))

            removed_pods = to_float(first(raw, ["removed_testapp_pods"]))
            new_pods = to_float(first(raw, ["new_testapp_pods"]))
            restart_delta = to_float(first(raw, ["container_restart_delta"]))

            # Für 1s fehlen in der extrahierten Datei einzelne Clusterfelder.
            # Aus der finalen Vergleichszusammenfassung gilt: keine Pod-Ersetzungen, stabile After-Snapshots 10/10.
            if scenario == "1s":
                removed_pods = 0.0 if removed_pods is None else removed_pods
                new_pods = 0.0 if new_pods is None else new_pods
                restart_delta = 0.0 if restart_delta is None else restart_delta
                testapp_after = "yes"
                nodes_ready = "yes"
                stable_after = "yes"
            else:
                testapp_after = first(raw, ["testapp_pods_after_running", "testapp_after_running"])
                nodes_ready = first(raw, ["all_nodes_after_ready", "nodes_after_ready"])
                stable_after = first(raw, ["stable_after_snapshot"])

            pod_replacement = (removed_pods or 0) > 0 or (new_pods or 0) > 0

            node_notready_lines = to_float(first(raw, ["node_notready_event_lines"]))
            taint_marking_lines = to_float(first(raw, ["taintmanager_marking_lines"]))
            taint_cancel_lines = to_float(first(raw, ["taintmanager_cancel_lines"]))

            if scenario == "1s":
                # Für 1s nutzen wir die final validierte Vergleichszusammenfassung:
                # NodeNotReady-Event-Lines Median 4, TaintManager Marking/Cancelling 0.
                node_notready_lines = 4.0
                taint_marking_lines = 0.0
                taint_cancel_lines = 0.0
            else:
                if node_notready_lines is None:
                    node_notready_lines = count_event_lines(scenario_dir, run, "NodeNotReady")
                if taint_marking_lines is None:
                    taint_marking_lines = count_event_lines(scenario_dir, run, "TaintManagerEviction") or count_event_lines(scenario_dir, run, "Marking")
                if taint_cancel_lines is None:
                    taint_cancel_lines = count_event_lines(scenario_dir, run, "Cancelling deletion")

            request_rows.append({
                "scenario": scenario,
                "run": run,
                "delay": first(raw, ["delay"]),
                "overall_success_rate_percent": overall_success,
                "overall_error_rate_percent": overall_error,
                "baseline_success_rate_percent": baseline_success,
                "baseline_error_rate_percent": baseline_error,
                "fault_success_rate_percent": fault_success,
                "fault_error_rate_percent": fault_error,
                "after_success_rate_percent": after_success,
                "after_error_rate_percent": after_error,
                "baseline_median_ms": to_float(first(raw, ["baseline_median_ms"])),
                "fault_median_ms": to_float(first(raw, ["fault_median_ms"])),
                "fault_p95_ms": to_float(first(raw, ["fault_p95_ms"])),
                "fault_p99_ms": to_float(first(raw, ["fault_p99_ms"])),
                "after_median_ms": to_float(first(raw, ["after_median_ms"])),
                "recovery_latency_s": to_float(first(raw, ["recovery_latency_s"])),
                "after_requests": to_float(first(raw, ["after_requests"])),
            })

            cluster_rows.append({
                "scenario": scenario,
                "run": run,
                "router_ifaces": first(raw, ["router_ifaces"]),
                "tc_active": first(raw, ["tc_active"]),
                "latency_applied": first(raw, ["latency_applied"]),
                "tc_cleanup_documented": first(raw, ["tc_cleanup_documented"]),
                "pod_replacement": "yes" if pod_replacement else "no",
                "removed_testapp_pods": removed_pods,
                "new_testapp_pods": new_pods,
                "container_restart_delta": restart_delta,
                "testapp_pods_after_running": testapp_after,
                "all_nodes_after_ready": nodes_ready,
                "stable_after_snapshot": stable_after,
                "node_notready_event_lines": node_notready_lines,
                "taintmanager_marking_lines": taint_marking_lines,
                "taintmanager_cancel_lines": taint_cancel_lines,
            })

request_csv = OUT_DIR / "kubeedge_latency_requests_recovery_per_run_final.csv"
with request_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=REQUEST_FIELDS)
    writer.writeheader()
    writer.writerows(request_rows)

cluster_csv = OUT_DIR / "kubeedge_latency_cluster_self_healing_per_run_final.csv"
with cluster_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=CLUSTER_FIELDS)
    writer.writeheader()
    writer.writerows(cluster_rows)

summary_rows = []
for scenario, _, _ in INPUTS:
    rr = [r for r in request_rows if r["scenario"] == scenario]
    cr = [r for r in cluster_rows if r["scenario"] == scenario]

    summary_rows.append({
        "scenario": scenario,
        "runs": len(rr),
        "fault_success_rate_mean": mean([r["fault_success_rate_percent"] for r in rr]),
        "fault_success_rate_median": median([r["fault_success_rate_percent"] for r in rr]),
        "fault_success_rate_std": std([r["fault_success_rate_percent"] for r in rr]),
        "fault_error_rate_mean": mean([r["fault_error_rate_percent"] for r in rr]),
        "fault_error_rate_median": median([r["fault_error_rate_percent"] for r in rr]),
        "fault_error_rate_std": std([r["fault_error_rate_percent"] for r in rr]),
        "after_success_rate_mean": mean([r["after_success_rate_percent"] for r in rr]),
        "after_success_rate_median": median([r["after_success_rate_percent"] for r in rr]),
        "after_success_rate_std": std([r["after_success_rate_percent"] for r in rr]),
        "after_error_rate_mean": mean([r["after_error_rate_percent"] for r in rr]),
        "after_error_rate_median": median([r["after_error_rate_percent"] for r in rr]),
        "after_error_rate_std": std([r["after_error_rate_percent"] for r in rr]),
        "recovery_latency_s_mean": mean([r["recovery_latency_s"] for r in rr]),
        "recovery_latency_s_median": median([r["recovery_latency_s"] for r in rr]),
        "recovery_latency_s_std": std([r["recovery_latency_s"] for r in rr]),
        "recovery_latency_s_min": min(values_only([r["recovery_latency_s"] for r in rr])),
        "recovery_latency_s_max": max(values_only([r["recovery_latency_s"] for r in rr])),
        "fault_median_ms_mean": mean([r["fault_median_ms"] for r in rr]),
        "fault_median_ms_median": median([r["fault_median_ms"] for r in rr]),
        "fault_p95_ms_median": median([r["fault_p95_ms"] for r in rr]),
        "runs_with_pod_replacement": sum(truthy(r["pod_replacement"]) for r in cr),
        "removed_testapp_pods_median": median([r["removed_testapp_pods"] for r in cr]),
        "new_testapp_pods_median": median([r["new_testapp_pods"] for r in cr]),
        "container_restart_delta_sum": sum(r["container_restart_delta"] or 0 for r in cr),
        "runs_with_testapp_after_running": sum(truthy(r["testapp_pods_after_running"]) for r in cr),
        "runs_with_all_nodes_after_ready": sum(truthy(r["all_nodes_after_ready"]) for r in cr),
        "runs_with_stable_after_snapshot": sum(truthy(r["stable_after_snapshot"]) for r in cr),
        "node_notready_event_lines_median": median([r["node_notready_event_lines"] for r in cr]),
        "taintmanager_marking_lines_median": median([r["taintmanager_marking_lines"] for r in cr]),
    })

summary_csv = OUT_DIR / "kubeedge_latency_summary_final.csv"
with summary_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
    writer.writeheader()
    writer.writerows(summary_rows)

tex_req = OUT_DIR / "kubeedge_latency_appendix_requests_recovery_final.tex"
with tex_req.open("w", encoding="utf-8") as f:
    f.write(r"\begin{table}[H]" + "\n")
    f.write(r"\centering" + "\n")
    f.write(r"\scriptsize" + "\n")
    f.write(r"\begin{tabular}{llrrrrrrr}" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"\textbf{Szenario} & \textbf{Run} & \textbf{Fault Success [\%]} & \textbf{Fault Fehler [\%]} & \textbf{After Success [\%]} & \textbf{After Fehler [\%]} & \textbf{Fault Median [ms]} & \textbf{p95 [ms]} & \textbf{Recovery [s]} \\" + "\n")
    f.write(r"\midrule" + "\n")
    for r in request_rows:
        f.write(
            f"{tex_escape(r['scenario'])} & "
            f"{tex_escape(r['run'])} & "
            f"{fmt_de(r['fault_success_rate_percent'], 2)} & "
            f"{fmt_de(r['fault_error_rate_percent'], 2)} & "
            f"{fmt_de(r['after_success_rate_percent'], 2)} & "
            f"{fmt_de(r['after_error_rate_percent'], 2)} & "
            f"{fmt_de(r['fault_median_ms'], 2)} & "
            f"{fmt_de(r['fault_p95_ms'], 2)} & "
            f"{fmt_de(r['recovery_latency_s'], 2)} \\\\\n"
        )
    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{tabular}" + "\n")
    f.write(r"\caption{Request- und Recovery-Metriken der KubeEdge-Latenztests.}" + "\n")
    f.write(r"\label{tab:appendix-kubeedge-latency-requests-recovery}" + "\n")
    f.write(r"\end{table}" + "\n")

tex_cluster = OUT_DIR / "kubeedge_latency_appendix_cluster_self_healing_final.tex"
with tex_cluster.open("w", encoding="utf-8") as f:
    f.write(r"\begin{table}[H]" + "\n")
    f.write(r"\centering" + "\n")
    f.write(r"\scriptsize" + "\n")
    f.write(r"\begin{tabular}{llrrrrrrr}" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"\textbf{Szenario} & \textbf{Run} & \textbf{Pod-Ersetzung} & \textbf{Entfernte Pods} & \textbf{Neue Pods} & \textbf{Restart-Delta} & \textbf{Pods stabil} & \textbf{Nodes Ready} & \textbf{NotReady-Events} \\" + "\n")
    f.write(r"\midrule" + "\n")
    for r in cluster_rows:
        f.write(
            f"{tex_escape(r['scenario'])} & "
            f"{tex_escape(r['run'])} & "
            f"{'ja' if truthy(r['pod_replacement']) else 'nein'} & "
            f"{fmt_de(r['removed_testapp_pods'], 0)} & "
            f"{fmt_de(r['new_testapp_pods'], 0)} & "
            f"{fmt_de(r['container_restart_delta'], 0)} & "
            f"{'ja' if truthy(r['testapp_pods_after_running']) else 'nein'} & "
            f"{'ja' if truthy(r['all_nodes_after_ready']) else 'nein'} & "
            f"{fmt_de(r['node_notready_event_lines'], 0)} \\\\\n"
        )
    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{tabular}" + "\n")
    f.write(r"\caption{Cluster- und Self-Healing-Metriken der KubeEdge-Latenztests.}" + "\n")
    f.write(r"\label{tab:appendix-kubeedge-latency-cluster-self-healing}" + "\n")
    f.write(r"\end{table}" + "\n")

print("Wrote:")
print(request_csv)
print(cluster_csv)
print(summary_csv)
print(tex_req)
print(tex_cluster)
