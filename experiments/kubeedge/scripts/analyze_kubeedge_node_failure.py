from pathlib import Path
import csv
import statistics

BASE = Path("experiments/kubeedge/node-failure")
OUT_DIR = BASE / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

INPUTS = [
    ("edge", BASE / "edge" / "edge-node-failure-summary.csv"),
    ("cloud", BASE / "cloud" / "cloud-node-failure-summary.csv"),
]

FIELDNAMES = [
    "run",
    "role",
    "failed_node",
    "url",
    "node_notready_detected",
    "node_ready_detected",
    "node_notready_seconds",
    "node_recovery_seconds",
    "vm_poweroff_to_ready_seconds",
    "vm_restart_to_ready_seconds",
    "total_requests",
    "ok_requests",
    "failed_requests",
    "success_rate_percent",
    "error_rate_percent",
    "median_latency_ms",
    "p95_latency_ms",
    "max_latency_ms",
    "error_types",
    "first_failed_request_time",
    "last_failed_request_time",
    "pod_restart_delta",
    "manual_prompt_reached",
    "manual_intervention_confirmed",
    "preflight_before_ok",
    "preflight_after_ok",
    "nodes_final_ready",
]

def fmt_de(value, digits=2):
    if value in (None, ""):
        return "--"
    try:
        return f"{float(value):.{digits}f}".replace(".", ",")
    except Exception:
        return str(value).replace(".", ",")

def tex_escape(s):
    s = "" if s is None else str(s)
    return (
        s.replace("_", r"\_")
         .replace("%", r"\%")
         .replace("&", r"\&")
         .replace("#", r"\#")
    )

def mean(vals):
    return statistics.mean(vals) if vals else None

def median(vals):
    return statistics.median(vals) if vals else None

def std(vals):
    return statistics.stdev(vals) if len(vals) > 1 else 0.0

def to_float(row, key):
    value = row.get(key, "")
    if value == "":
        return 0.0
    return float(value)

rows = []

for role, path in INPUTS:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {k: "" for k in FIELDNAMES}

            for k, v in raw.items():
                if k in row:
                    row[k] = v

            row["role"] = role

            # Spalten vereinheitlichen:
            # Edge-Datei nutzt manual_intervention,
            # Cloud-Datei nutzt manual_prompt_reached/manual_intervention_confirmed.
            if role == "edge":
                row["manual_prompt_reached"] = "False"
                row["manual_intervention_confirmed"] = raw.get("manual_intervention", "False")
            else:
                row["manual_prompt_reached"] = raw.get("manual_prompt_reached", "False")
                row["manual_intervention_confirmed"] = raw.get("manual_intervention_confirmed", "False")

            for key in [
                "node_notready_seconds",
                "node_recovery_seconds",
                "vm_poweroff_to_ready_seconds",
                "vm_restart_to_ready_seconds",
                "total_requests",
                "ok_requests",
                "failed_requests",
                "success_rate_percent",
                "error_rate_percent",
                "median_latency_ms",
                "p95_latency_ms",
                "max_latency_ms",
                "pod_restart_delta",
            ]:
                if row[key] != "":
                    row[key] = float(row[key])

            rows.append(row)

per_run_path = OUT_DIR / "kubeedge_node_failure_per_run_final.csv"
with per_run_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)

summary_rows = []
for role in ["edge", "cloud"]:
    rr = [r for r in rows if r["role"] == role]
    summary_rows.append({
        "role": role,
        "runs_total": len(rr),
        "node_notready_detected_runs": sum(str(r["node_notready_detected"]).lower() == "true" for r in rr),
        "node_ready_detected_runs": sum(str(r["node_ready_detected"]).lower() == "true" for r in rr),
        "success_rate_mean_percent": mean([r["success_rate_percent"] for r in rr]),
        "success_rate_median_percent": median([r["success_rate_percent"] for r in rr]),
        "success_rate_std_percent": std([r["success_rate_percent"] for r in rr]),
        "success_rate_min_percent": min(r["success_rate_percent"] for r in rr),
        "success_rate_max_percent": max(r["success_rate_percent"] for r in rr),
        "error_rate_mean_percent": mean([r["error_rate_percent"] for r in rr]),
        "error_rate_max_percent": max(r["error_rate_percent"] for r in rr),
        "node_notready_seconds_mean": mean([r["node_notready_seconds"] for r in rr]),
        "node_notready_seconds_median": median([r["node_notready_seconds"] for r in rr]),
        "node_notready_seconds_min": min(r["node_notready_seconds"] for r in rr),
        "node_notready_seconds_max": max(r["node_notready_seconds"] for r in rr),
        "node_recovery_seconds_mean": mean([r["node_recovery_seconds"] for r in rr]),
        "node_recovery_seconds_median": median([r["node_recovery_seconds"] for r in rr]),
        "node_recovery_seconds_min": min(r["node_recovery_seconds"] for r in rr),
        "node_recovery_seconds_max": max(r["node_recovery_seconds"] for r in rr),
        "vm_restart_to_ready_seconds_mean": mean([r["vm_restart_to_ready_seconds"] for r in rr]),
        "vm_restart_to_ready_seconds_median": median([r["vm_restart_to_ready_seconds"] for r in rr]),
        "total_requests": int(sum(r["total_requests"] for r in rr)),
        "ok_requests": int(sum(r["ok_requests"] for r in rr)),
        "failed_requests": int(sum(r["failed_requests"] for r in rr)),
        "pod_restart_delta_sum": int(sum(r["pod_restart_delta"] for r in rr)),
        "manual_interventions": sum(str(r["manual_intervention_confirmed"]).lower() == "true" for r in rr),
        "nodes_final_ready_runs": sum(str(r["nodes_final_ready"]).lower() == "true" for r in rr),
    })

summary_path = OUT_DIR / "kubeedge_node_failure_summary_final.csv"
with summary_path.open("w", encoding="utf-8", newline="") as f:
    fieldnames = list(summary_rows[0].keys())
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(summary_rows)

tex_req = OUT_DIR / "kubeedge_node_failure_appendix_requests_final.tex"
with tex_req.open("w", encoding="utf-8") as f:
    f.write(r"\begin{table}[H]" + "\n")
    f.write(r"\centering" + "\n")
    f.write(r"\begin{tabular}{llrrrrrr}" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"\textbf{Run} & \textbf{Rolle} & \textbf{Req.} & \textbf{OK} & \textbf{Fail} & \textbf{Success [\%]} & \textbf{Fehler [\%]} & \textbf{Restarts} \\" + "\n")
    f.write(r"\midrule" + "\n")
    for r in rows:
        f.write(
            f"{tex_escape(r['run'])} & "
            f"{tex_escape(r['role'])} & "
            f"{int(r['total_requests'])} & "
            f"{int(r['ok_requests'])} & "
            f"{int(r['failed_requests'])} & "
            f"{fmt_de(r['success_rate_percent'], 2)} & "
            f"{fmt_de(r['error_rate_percent'], 2)} & "
            f"{int(r['pod_restart_delta'])} \\\\\n"
        )
    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{tabular}" + "\n")
    f.write(r"\caption{Request- und Workload-Metriken der KubeEdge-Node-Ausfalltests.}" + "\n")
    f.write(r"\label{tab:appendix-kubeedge-node-failure-requests}" + "\n")
    f.write(r"\end{table}" + "\n")

tex_nodes = OUT_DIR / "kubeedge_node_failure_appendix_nodes_final.tex"
with tex_nodes.open("w", encoding="utf-8") as f:
    f.write(r"\begin{table}[H]" + "\n")
    f.write(r"\centering" + "\n")
    f.write(r"\begin{tabular}{lllrrrr}" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"\textbf{Run} & \textbf{Rolle} & \textbf{Node} & \textbf{NotReady [s]} & \textbf{Recovery [s]} & \textbf{Restart--Ready [s]} & \textbf{Final Ready} \\" + "\n")
    f.write(r"\midrule" + "\n")
    for r in rows:
        f.write(
            f"{tex_escape(r['run'])} & "
            f"{tex_escape(r['role'])} & "
            f"{tex_escape(r['failed_node'])} & "
            f"{fmt_de(r['node_notready_seconds'], 1)} & "
            f"{fmt_de(r['node_recovery_seconds'], 1)} & "
            f"{fmt_de(r['vm_restart_to_ready_seconds'], 1)} & "
            f"{'ja' if str(r['nodes_final_ready']).lower() == 'true' else 'nein'} \\\\\n"
        )
    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{tabular}" + "\n")
    f.write(r"\caption{Node-Status- und Recovery-Metriken der KubeEdge-Node-Ausfalltests.}" + "\n")
    f.write(r"\label{tab:appendix-kubeedge-node-failure-nodes}" + "\n")
    f.write(r"\end{table}" + "\n")

print("Wrote:")
print(per_run_path)
print(summary_path)
print(tex_req)
print(tex_nodes)
