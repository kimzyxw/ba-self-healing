import csv
import statistics
from pathlib import Path

BASE = Path("experiments/k3s/packet-loss-tests/analysis")

IN_PER_RUN = BASE / "k3s_packet_loss_per_run.csv"
IN_PER_PHASE = BASE / "k3s_packet_loss_per_phase.csv"

FINAL_SCENARIOS = [
    "packet-loss-1pct-async-limited",
    "packet-loss-10pct-async-limited",
    "packet-loss-50pct-async-limited",
    "packet-loss-70pct-router-cleanup",
    "packet-loss-100pct-safety-cleanup",
]

SCENARIO_LABELS = {
    "packet-loss-1pct-async-limited": "1\\%",
    "packet-loss-10pct-async-limited": "10\\%",
    "packet-loss-50pct-async-limited": "50\\%",
    "packet-loss-70pct-router-cleanup": "70\\%",
    "packet-loss-100pct-safety-cleanup": "100\\%",
}

SCENARIO_ORDER = {name: i for i, name in enumerate(FINAL_SCENARIOS)}


def read_csv(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"No rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def to_float(v):
    if v is None or v == "" or v == "NA":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def to_int(v):
    f = to_float(v)
    return int(f) if f is not None else None


def valid_fault_row(r):
    req = to_int(r.get("fault_requests_total"))
    return (
        r["scenario"] in FINAL_SCENARIOS
        and req is not None
        and req > 0
        and r.get("fault_success_rate_percent", "") != ""
        and r.get("fault_error_rate_percent", "") != ""
    )


def valid_recovery_row(r):
    return r["scenario"] in FINAL_SCENARIOS and str(r.get("recovery_observed", "")).lower() == "true"


def vals(rows, key):
    out = []
    for r in rows:
        v = to_float(r.get(key))
        if v is not None:
            out.append(v)
    return out


def mean(v):
    return statistics.mean(v) if v else None


def stdev(v):
    if not v:
        return None
    return statistics.stdev(v) if len(v) > 1 else 0.0


def fmt_csv(v):
    return "" if v is None else v


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


def short_run(r):
    return r.replace("run-", "").replace("-router", "")


per_run_all = read_csv(IN_PER_RUN)
per_phase_all = read_csv(IN_PER_PHASE)

per_run = [r for r in per_run_all if r["scenario"] in FINAL_SCENARIOS]
per_phase = [r for r in per_phase_all if r["scenario"] in FINAL_SCENARIOS]

per_run.sort(key=lambda r: (SCENARIO_ORDER[r["scenario"]], r["run"]))
per_phase.sort(key=lambda r: (SCENARIO_ORDER[r["scenario"]], r["run"], r["phase"]))

# Add explicit validity flags
for r in per_run:
    is_valid = valid_fault_row(r)
    r["valid_for_fault_metrics"] = "true" if is_valid else "false"
    if not is_valid:
        r["validity_note"] = "monitor_vor_fault_beendet"
    else:
        r["validity_note"] = "valid"

write_csv(BASE / "k3s_packet_loss_per_run_final.csv", per_run)
write_csv(BASE / "k3s_packet_loss_per_phase_final.csv", per_phase)

summary_rows = []

for scenario in FINAL_SCENARIOS:
    rows_total = [r for r in per_run if r["scenario"] == scenario]
    rows_valid = [r for r in rows_total if valid_fault_row(r)]
    rows_recovery = [r for r in rows_total if valid_recovery_row(r)]

    success = vals(rows_valid, "fault_success_rate_percent")
    error = vals(rows_valid, "fault_error_rate_percent")
    median_ms = vals(rows_valid, "fault_median_ms")
    p95_ms = vals(rows_valid, "fault_p95_ms")
    p99_ms = vals(rows_valid, "fault_p99_ms")
    max_ms = vals(rows_valid, "fault_max_ms")
    recovery = vals(rows_recovery, "recovery_time_s")

    summary_rows.append({
        "scenario": scenario,
        "runs_total": len(rows_total),
        "runs_valid_for_fault_metrics": len(rows_valid),
        "runs_invalid_fault_requests_0": len(rows_total) - len(rows_valid),

        "fault_success_rate_mean_percent": fmt_csv(mean(success)),
        "fault_success_rate_std_percent": fmt_csv(stdev(success)),
        "fault_success_rate_min_percent": min(success) if success else "",
        "fault_success_rate_max_percent": max(success) if success else "",

        "fault_error_rate_mean_percent": fmt_csv(mean(error)),
        "fault_error_rate_std_percent": fmt_csv(stdev(error)),

        "fault_median_ms_mean": fmt_csv(mean(median_ms)),
        "fault_median_ms_std": fmt_csv(stdev(median_ms)),
        "fault_p95_ms_mean": fmt_csv(mean(p95_ms)),
        "fault_p95_ms_std": fmt_csv(stdev(p95_ms)),
        "fault_p99_ms_mean": fmt_csv(mean(p99_ms)),
        "fault_p99_ms_std": fmt_csv(stdev(p99_ms)),
        "fault_max_ms_max": max(max_ms) if max_ms else "",

        "recovery_observed_runs": len(rows_recovery),
        "recovery_unobserved_runs": len(rows_total) - len(rows_recovery),
        "recovery_time_s_mean_observed_only": fmt_csv(mean(recovery)),
        "recovery_time_s_std_observed_only": fmt_csv(stdev(recovery)),
        "recovery_time_s_min_observed_only": min(recovery) if recovery else "",
        "recovery_time_s_max_observed_only": max(recovery) if recovery else "",

        "cluster_stable_final_snapshot_runs": sum(1 for r in rows_total if str(r["cluster_stabilization_observed"]).lower() == "true"),
        "cluster_stabilization_time_quantifiable_runs": sum(1 for r in rows_total if r["cluster_stabilization_time_s"] != ""),

        "testapp_pod_restart_delta_total": sum(to_int(r["testapp_pod_restart_delta"]) or 0 for r in rows_total),
        "testapp_pod_restart_runs": sum(1 for r in rows_total if (to_int(r["testapp_pod_restart_delta"]) or 0) > 0),
        "testapp_pod_recreated_runs": sum(1 for r in rows_total if (to_int(r["testapp_pods_new_after_count"]) or 0) > 0 or (to_int(r["testapp_pods_disappeared_count"]) or 0) > 0),
        "testapp_pod_rescheduled_runs": sum(1 for r in rows_total if (to_int(r["testapp_pod_node_changes_count"]) or 0) > 0),

        "node_notready_new_event_runs": sum(1 for r in rows_total if (to_int(r["node_notready_new_events"]) or 0) > 0),
        "node_notready_new_events_total": sum(to_int(r["node_notready_new_events"]) or 0 for r in rows_total),
        "node_final_not_all_ready_runs": sum(1 for r in rows_total if str(r["node_final_all_ready"]).lower() != "true"),

        "self_healing_workload_runs": sum(1 for r in rows_total if r["self_healing_classification"] == "yes_workload_healing"),
        "node_reachability_event_only_runs": sum(1 for r in rows_total if r["self_healing_classification"] == "node_reachability_event_only"),
    })

write_csv(BASE / "k3s_packet_loss_summary_final.csv", summary_rows)

# Appendix table 1: request/recovery
with (BASE / "k3s_packet_loss_appendix_requests_final.tex").open("w", encoding="utf-8") as f:
    f.write("% Automatically generated final compact request/recovery appendix table\n")
    f.write(r"\begin{longtable}{llrrrrrrrrl}" + "\n")
    f.write(r"\caption{Einzelwerte der K3s-Paketverlusttests: Request- und Recovery-Metriken}\label{tab:appendix-k3s-packet-loss-requests}\\" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Verlust & Run & Req. & OK & Fail & Succ. [\%] & Err. [\%] & Med. [ms] & p95 [ms] & Rec. [s] & Status \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endfirsthead" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Verlust & Run & Req. & OK & Fail & Succ. [\%] & Err. [\%] & Med. [ms] & p95 [ms] & Rec. [s] & Status \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endhead" + "\n")

    for r in per_run:
        status = "ok" if r["valid_for_fault_metrics"] == "true" else "Monitor vor Fault beendet"
        f.write(
            f"{SCENARIO_LABELS[r['scenario']]} & "
            f"{esc(short_run(r['run']))} & "
            f"{de(r['fault_requests_total'])} & "
            f"{de(r['fault_success'])} & "
            f"{de(r['fault_failed'])} & "
            f"{de(r['fault_success_rate_percent'])} & "
            f"{de(r['fault_error_rate_percent'])} & "
            f"{de(r['fault_median_ms'])} & "
            f"{de(r['fault_p95_ms'])} & "
            f"{de(r['recovery_time_s'])} & "
            f"{esc(status)} \\\\\n"
        )

    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{longtable}" + "\n")

# Appendix table 2: cluster/self-healing
with (BASE / "k3s_packet_loss_appendix_cluster_final.tex").open("w", encoding="utf-8") as f:
    f.write("% Automatically generated final compact cluster/self-healing appendix table\n")
    f.write(r"\begin{longtable}{llrrrrrll}" + "\n")
    f.write(r"\caption{Einzelwerte der K3s-Paketverlusttests: Clusterzustand und Self-Healing-Metriken}\label{tab:appendix-k3s-packet-loss-cluster}\\" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Verlust & Run & Pod-Rest. & Pod neu & Pod weg & Resched. & NodeNotReady & Final Ready & Self-Healing \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endfirsthead" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Verlust & Run & Pod-Rest. & Pod neu & Pod weg & Resched. & NodeNotReady & Final Ready & Self-Healing \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endhead" + "\n")

    for r in per_run:
        cls_short = {
            "no": "nein",
            "node_reachability_event_only": "Node-Event",
            "yes_workload_healing": "Workload",
        }.get(r["self_healing_classification"], r["self_healing_classification"])

        f.write(
            f"{SCENARIO_LABELS[r['scenario']]} & "
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

print("Wrote final packet-loss analysis files:")
print(BASE / "k3s_packet_loss_per_run_final.csv")
print(BASE / "k3s_packet_loss_per_phase_final.csv")
print(BASE / "k3s_packet_loss_summary_final.csv")
print(BASE / "k3s_packet_loss_appendix_requests_final.tex")
print(BASE / "k3s_packet_loss_appendix_cluster_final.tex")
