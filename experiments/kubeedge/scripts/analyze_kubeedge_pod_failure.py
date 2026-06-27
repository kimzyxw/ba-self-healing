from pathlib import Path
import csv
import statistics
import re

BASE = Path("experiments/kubeedge/pod-failure")
OUT_DIR = BASE / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_CSV = BASE / "pod-failure-summary.csv"

def tex_escape(s):
    if s is None:
        return ""
    s = str(s)
    repl = {
        "_": r"\_",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s

def fmt_de(value, digits=2):
    if value is None or value == "":
        return "--"
    try:
        return f"{float(value):.{digits}f}".replace(".", ",")
    except Exception:
        return str(value).replace(".", ",")

def parse_pods(path):
    pods = {}
    if not path.exists():
        return pods
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 7 and parts[0].startswith("nginx-testapp-"):
            pods[parts[0]] = {
                "ready": parts[1],
                "status": parts[2],
                "restarts": int(parts[3]) if parts[3].isdigit() else 0,
                "age": parts[4],
                "ip": parts[5],
                "node": parts[6],
            }
    return pods

def parse_nodes_ready(path):
    if not path.exists():
        return False, ""
    statuses = []
    nodes = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 2:
            nodes.append(parts[0])
            statuses.append(parts[1])
    return bool(statuses) and all(s == "Ready" for s in statuses), ";".join(f"{n}:{s}" for n, s in zip(nodes, statuses))

rows = []
with SUMMARY_CSV.open(encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        run = row["run"]
        run_dir = BASE / run

        pods_before = parse_pods(run_dir / "pods_before.txt")
        pods_after = parse_pods(run_dir / "pods_after.txt")

        before_names = set(pods_before)
        after_names = set(pods_after)

        deleted_pod = row["deleted_pod"]
        new_pods = sorted(after_names - before_names)
        deleted_absent_after = deleted_pod not in after_names

        new_pod = new_pods[0] if new_pods else ""
        new_pod_node = pods_after.get(new_pod, {}).get("node", "")
        deleted_pod_node = row["deleted_pod_node"]

        recreated = len(new_pods) >= 1 and deleted_absent_after
        rescheduled = bool(new_pod_node and deleted_pod_node and new_pod_node != deleted_pod_node)

        final_ready, final_node_status = parse_nodes_ready(run_dir / "nodes_after.txt")

        rows.append({
            "run": run,
            "deleted_pod": deleted_pod,
            "deleted_pod_node": deleted_pod_node,
            "new_pod": new_pod,
            "new_pod_node": new_pod_node,
            "pod_recreated": recreated,
            "rescheduled": rescheduled,
            "recovered": row["recovered"],
            "recovery_seconds": float(row["recovery_seconds"]),
            "total_requests": int(row["total_requests"]),
            "ok_requests": int(row["ok_requests"]),
            "failed_requests": int(row["failed_requests"]),
            "success_rate_percent": float(row["success_rate_percent"]),
            "error_rate_percent": float(row["error_rate_percent"]),
            "median_ms": float(row["median_ms"]),
            "p95_ms": float(row["p95_ms"]),
            "max_ms": float(row["max_ms"]),
            "pod_restarts_before": int(row["pod_restarts_before"]),
            "pod_restarts_after": int(row["pod_restarts_after"]),
            "pod_restart_delta": int(row["pod_restarts_after"]) - int(row["pod_restarts_before"]),
            "node_final_all_ready": final_ready,
            "node_status_after": final_node_status,
        })

# Write enriched per-run CSV
per_run_path = OUT_DIR / "kubeedge_pod_failure_per_run_final.csv"
with per_run_path.open("w", encoding="utf-8", newline="") as f:
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# Write aggregate CSV
def mean(vals):
    return statistics.mean(vals) if vals else None

def median(vals):
    return statistics.median(vals) if vals else None

def std(vals):
    return statistics.stdev(vals) if len(vals) > 1 else 0.0

summary = {
    "runs_total": len(rows),
    "recovered_runs": sum(1 for r in rows if str(r["recovered"]).lower() == "true"),
    "success_rate_mean_percent": mean([r["success_rate_percent"] for r in rows]),
    "success_rate_std_percent": std([r["success_rate_percent"] for r in rows]),
    "error_rate_mean_percent": mean([r["error_rate_percent"] for r in rows]),
    "error_rate_std_percent": std([r["error_rate_percent"] for r in rows]),
    "recovery_seconds_mean": mean([r["recovery_seconds"] for r in rows]),
    "recovery_seconds_median": median([r["recovery_seconds"] for r in rows]),
    "recovery_seconds_std": std([r["recovery_seconds"] for r in rows]),
    "recovery_seconds_min": min(r["recovery_seconds"] for r in rows),
    "recovery_seconds_max": max(r["recovery_seconds"] for r in rows),
    "pod_recreated_runs": sum(1 for r in rows if r["pod_recreated"]),
    "pod_rescheduled_runs": sum(1 for r in rows if r["rescheduled"]),
    "pod_restart_delta_total": sum(r["pod_restart_delta"] for r in rows),
    "node_final_all_ready_runs": sum(1 for r in rows if r["node_final_all_ready"]),
}

summary_path = OUT_DIR / "kubeedge_pod_failure_summary_final.csv"
with summary_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
    writer.writeheader()
    writer.writerow(summary)

# Appendix table: requests/recovery
tex_req = OUT_DIR / "kubeedge_pod_failure_appendix_requests_final.tex"
with tex_req.open("w", encoding="utf-8") as f:
    f.write(r"\begin{table}[H]" + "\n")
    f.write(r"\centering" + "\n")
    f.write(r"\begin{tabular}{lrrrrrr}" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"\textbf{Run} & \textbf{Req.} & \textbf{OK} & \textbf{Fail} & \textbf{Success [\%]} & \textbf{Fehler [\%]} & \textbf{Recovery [s]} \\" + "\n")
    f.write(r"\midrule" + "\n")
    for r in rows:
        f.write(
            f"{tex_escape(r['run'])} & "
            f"{r['total_requests']} & "
            f"{r['ok_requests']} & "
            f"{r['failed_requests']} & "
            f"{fmt_de(r['success_rate_percent'], 2)} & "
            f"{fmt_de(r['error_rate_percent'], 2)} & "
            f"{fmt_de(r['recovery_seconds'], 1)} \\\\\n"
        )
    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{tabular}" + "\n")
    f.write(r"\caption{Request- und Recovery-Metriken der KubeEdge-Pod-Ausfalltests.}" + "\n")
    f.write(r"\label{tab:appendix-kubeedge-pod-failure-requests}" + "\n")
    f.write(r"\end{table}" + "\n")

# Appendix table: self-healing/cluster
tex_cluster = OUT_DIR / "kubeedge_pod_failure_appendix_cluster_final.tex"
with tex_cluster.open("w", encoding="utf-8") as f:
    f.write(r"\begin{table}[H]" + "\n")
    f.write(r"\centering" + "\n")
    f.write(r"\begin{tabular}{llllrrl}" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"\textbf{Run} & \textbf{gelöschter Node} & \textbf{neuer Node} & \textbf{Pod ersetzt} & \textbf{Resched.} & \textbf{Restarts} & \textbf{Nodes final} \\" + "\n")
    f.write(r"\midrule" + "\n")
    for r in rows:
        f.write(
            f"{tex_escape(r['run'])} & "
            f"{tex_escape(r['deleted_pod_node'])} & "
            f"{tex_escape(r['new_pod_node'])} & "
            f"{'ja' if r['pod_recreated'] else 'nein'} & "
            f"{'ja' if r['rescheduled'] else 'nein'} & "
            f"{r['pod_restart_delta']} & "
            f"{'Ready' if r['node_final_all_ready'] else 'nicht vollständig Ready'} \\\\\n"
        )
    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{tabular}" + "\n")
    f.write(r"\caption{Cluster- und Self-Healing-Metriken der KubeEdge-Pod-Ausfalltests.}" + "\n")
    f.write(r"\label{tab:appendix-kubeedge-pod-failure-cluster}" + "\n")
    f.write(r"\end{table}" + "\n")

print("Wrote:")
print(per_run_path)
print(summary_path)
print(tex_req)
print(tex_cluster)
