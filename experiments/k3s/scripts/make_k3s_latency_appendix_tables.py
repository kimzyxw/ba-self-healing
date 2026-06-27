import csv
from pathlib import Path

IN = Path("experiments/k3s/latency-tests/analysis/k3s_latency_per_run.csv")
OUT = Path("experiments/k3s/latency-tests/analysis")

def esc(s):
    s = str(s)
    return (
        s.replace("_", r"\_")
         .replace("%", r"\%")
         .replace("&", r"\&")
         .replace("#", r"\#")
    )

def de(v, digits=2):
    if v is None or v == "":
        return "--"
    if str(v).lower() == "true":
        return "ja"
    if str(v).lower() == "false":
        return "nein"
    try:
        f = float(v)
        if f.is_integer():
            return str(int(f))
        return f"{f:.{digits}f}".replace(".", ",")
    except ValueError:
        return esc(v)

def short_scenario(s):
    mapping = {
        "latency-1s-short": "1s",
        "latency-1min-short": "1min",
        "latency-10min-async-limited": "10min",
        "latency-30min-async-limited": "30min",
    }
    return mapping.get(s, s)

def short_run(r):
    return r.replace("run-", "").replace("-router", "")

rows = list(csv.DictReader(IN.open(encoding="utf-8")))

# Tabelle 1: Request + Recovery
with (OUT / "k3s_latency_appendix_requests.tex").open("w", encoding="utf-8") as f:
    f.write("% Automatically generated compact request/recovery appendix table\n")
    f.write(r"\begin{longtable}{llrrrrrrrr}" + "\n")
    f.write(r"\caption{Einzelwerte der K3s-Latenztests: Request- und Recovery-Metriken}\label{tab:appendix-k3s-latency-requests}\\" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Szen. & Run & Req. & OK & Fail & Succ. [\%] & Err. [\%] & Med. [ms] & p95 [ms] & Rec. [s] \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endfirsthead" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Szen. & Run & Req. & OK & Fail & Succ. [\%] & Err. [\%] & Med. [ms] & p95 [ms] & Rec. [s] \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endhead" + "\n")

    for r in rows:
        f.write(
            f"{esc(short_scenario(r['scenario']))} & "
            f"{esc(short_run(r['run']))} & "
            f"{de(r['fault_requests_total'])} & "
            f"{de(r['fault_success'])} & "
            f"{de(r['fault_failed'])} & "
            f"{de(r['fault_success_rate_percent'])} & "
            f"{de(r['fault_error_rate_percent'])} & "
            f"{de(r['fault_median_ms'])} & "
            f"{de(r['fault_p95_ms'])} & "
            f"{de(r['recovery_time_s'])} \\\\\n"
        )

    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{longtable}" + "\n")

# Tabelle 2: Cluster + Self-Healing
with (OUT / "k3s_latency_appendix_cluster.tex").open("w", encoding="utf-8") as f:
    f.write("% Automatically generated compact cluster/self-healing appendix table\n")
    f.write(r"\begin{longtable}{llrrrrrll}" + "\n")
    f.write(r"\caption{Einzelwerte der K3s-Latenztests: Clusterzustand und Self-Healing-Metriken}\label{tab:appendix-k3s-latency-cluster}\\" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Szen. & Run & Pod-Rest. & Pod neu & Pod weg & Resched. & NodeNotReady & Final Ready & Self-Healing \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endfirsthead" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Szen. & Run & Pod-Rest. & Pod neu & Pod weg & Resched. & NodeNotReady & Final Ready & Self-Healing \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endhead" + "\n")

    for r in rows:
        cls = r["self_healing_classification"]
        cls_short = {
            "no": "nein",
            "node_reachability_event_only": "Node-Event",
            "yes_workload_healing": "Workload",
        }.get(cls, cls)

        f.write(
            f"{esc(short_scenario(r['scenario']))} & "
            f"{esc(short_run(r['run']))} & "
            f"{de(r['testapp_pod_restart_delta'])} & "
            f"{de(r['testapp_pods_new_after_count'])} & "
            f"{de(r['testapp_pods_disappeared_count'])} & "
            f"{de(r['testapp_pod_node_changes_count'])} & "
            f"{de(r['node_notready_new_events'])} & "
            f"{de(r['node_final_all_ready'])} & "
            f"{esc(cls_short)} \\\\\n"
        )

    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{longtable}" + "\n")

print("Wrote", OUT / "k3s_latency_appendix_requests.tex")
print("Wrote", OUT / "k3s_latency_appendix_cluster.tex")
