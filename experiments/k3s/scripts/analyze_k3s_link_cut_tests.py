from pathlib import Path
import csv
import re
import statistics
from typing import Dict, List, Optional, Tuple

BASE = Path("experiments/k3s/link-cut-tests")
OUT_DIR = BASE / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FINAL_SCENARIOS = [
    "link-cut-1s",
    "link-cut-1min",
    "link-cut-10min",
    "link-cut-30min",
]

SCENARIO_LABELS = {
    "link-cut-1s": "1s",
    "link-cut-1min": "1min",
    "link-cut-10min": "10min",
    "link-cut-30min": "30min",
}

SCENARIO_ORDER = {name: i for i, name in enumerate(FINAL_SCENARIOS)}

EVENT_PATTERNS = [
    "NodeNotReady",
    "NodeNotReachable",
    "FailedScheduling",
    "FailedCreatePodSandBox",
    "BackOff",
    "Evicted",
    "Unhealthy",
    "FailedMount",
    "CrashLoopBackOff",
    "Killing",
]

POD_PROBLEM_STATES = [
    "Pending",
    "CrashLoopBackOff",
    "Error",
    "Evicted",
    "Terminating",
    "ContainerCreating",
    "ImagePullBackOff",
    "Unknown",
]


def parse_summary(path: Path) -> Dict:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    data = {"meta": {}}
    current = "meta"

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if line.startswith("--- ") and line.endswith(" ---"):
            current = line.replace("---", "").strip()
            data[current] = {}
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            data[current][key.strip()] = value.strip()

    return data


def to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    value = str(value).strip().replace("%", "")
    if value == "" or value == "NA":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def to_int(value: Optional[str]) -> Optional[int]:
    f = to_float(value)
    return int(f) if f is not None else None


def read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def normalize_event_line(line: str) -> str:
    return re.sub(r"^\S+\s+\S+\s+", "", line).strip()


def matching_event_lines(path: Path) -> List[str]:
    lines = []
    for line in read_lines(path):
        if any(p in line for p in EVENT_PATTERNS):
            lines.append(normalize_event_line(line))
    return lines


def event_diff(run_dir: Path) -> Dict:
    before = matching_event_lines(run_dir / "events_before.txt")
    after = matching_event_lines(run_dir / "events_after.txt")

    new = [line for line in after if line not in before]

    node_notready_new = [line for line in new if "NodeNotReady" in line]
    node_notreachable_new = [line for line in new if "NodeNotReachable" in line]
    unhealthy_new = [line for line in new if "Unhealthy" in line]

    return {
        "event_matches_before": len(before),
        "event_matches_after": len(after),
        "event_new_after_only": len(new),
        "node_notready_new_events": len(node_notready_new),
        "node_notreachable_new_events": len(node_notreachable_new),
        "unhealthy_new_events": len(unhealthy_new),
        "new_event_lines": " | ".join(new),
    }


def parse_nodes(path: Path) -> Dict[str, str]:
    nodes = {}
    for line in read_lines(path):
        line = line.rstrip()
        if not line or line.startswith("NAME"):
            continue
        parts = re.split(r"\s+", line)
        if len(parts) >= 2:
            nodes[parts[0]] = parts[1]
    return nodes


def node_status_analysis(run_dir: Path) -> Dict:
    before = parse_nodes(run_dir / "nodes_before.txt")
    after = parse_nodes(run_dir / "nodes_after.txt")

    all_nodes = sorted(set(before) | set(after))
    before_statuses = []
    after_statuses = []
    changed = []

    for node in all_nodes:
        b = before.get(node, "MISSING")
        a = after.get(node, "MISSING")
        before_statuses.append(f"{node}:{b}")
        after_statuses.append(f"{node}:{a}")
        if b != a:
            changed.append(f"{node}:{b}->{a}")

    before_problem_nodes = [n for n, s in before.items() if s in ["NotReady", "Unknown"]]
    after_problem_nodes = [n for n, s in after.items() if s in ["NotReady", "Unknown"]]

    final_all_ready = bool(after) and all(s == "Ready" for s in after.values())

    return {
        "node_status_before": " | ".join(before_statuses),
        "node_status_after": " | ".join(after_statuses),
        "node_status_changed_count": len(changed),
        "node_status_changes": " | ".join(changed),
        "node_problem_before_count": len(before_problem_nodes),
        "node_problem_after_count": len(after_problem_nodes),
        "node_problem_before": " | ".join(before_problem_nodes),
        "node_problem_after": " | ".join(after_problem_nodes),
        "node_final_all_ready": final_all_ready,
    }


def parse_restart_value(raw: str) -> int:
    match = re.match(r"^(\d+)", raw.strip())
    return int(match.group(1)) if match else 0


def parse_testapp_pods(path: Path) -> Dict[str, Dict]:
    pods = {}

    for line in read_lines(path):
        if "testapp" not in line and "nginx-test" not in line:
            continue

        parts = re.split(r"\s+", line.strip())
        if len(parts) < 8:
            continue

        namespace = parts[0]
        name = parts[1]
        ready = parts[2]
        status = parts[3]

        restarts_raw = parts[4]
        age_index = 5
        if len(parts) > 6 and parts[5].startswith("("):
            restarts_raw = parts[4] + " " + parts[5] + (" " + parts[6] if len(parts) > 6 else "")
            age_index = 7

        restarts = parse_restart_value(restarts_raw)

        node = "UNKNOWN"
        if len(parts) > age_index + 2:
            node = parts[age_index + 2]

        pods[name] = {
            "namespace": namespace,
            "name": name,
            "ready": ready,
            "status": status,
            "restarts": restarts,
            "node": node,
            "raw": line.strip(),
        }

    return pods


def pod_analysis(run_dir: Path) -> Dict:
    before = parse_testapp_pods(run_dir / "pods_before.txt")
    after = parse_testapp_pods(run_dir / "pods_after.txt")

    before_names = set(before.keys())
    after_names = set(after.keys())

    recreated_or_new = sorted(after_names - before_names)
    disappeared = sorted(before_names - after_names)
    common = sorted(before_names & after_names)

    restart_delta = 0
    restart_changes = []
    node_changes = []
    status_problem_after = []

    for name in common:
        b = before[name]
        a = after[name]

        delta = a["restarts"] - b["restarts"]
        restart_delta += delta

        if delta != 0:
            restart_changes.append(f"{name}:{b['restarts']}->{a['restarts']}")

        if b["node"] != a["node"]:
            node_changes.append(f"{name}:{b['node']}->{a['node']}")

    for name, pod in after.items():
        if pod["status"] != "Running":
            status_problem_after.append(f"{name}:{pod['status']}")

    pod_problem_count_text = 0
    for file_name in ["pods_before.txt", "pods_after.txt"]:
        text = "\n".join(read_lines(run_dir / file_name))
        for state in POD_PROBLEM_STATES:
            pod_problem_count_text += text.count(state)

    return {
        "testapp_pods_before_count": len(before),
        "testapp_pods_after_count": len(after),
        "testapp_pod_restart_delta": restart_delta,
        "testapp_pod_restart_changes": " | ".join(restart_changes),
        "testapp_pods_new_after_count": len(recreated_or_new),
        "testapp_pods_new_after": " | ".join(recreated_or_new),
        "testapp_pods_disappeared_count": len(disappeared),
        "testapp_pods_disappeared": " | ".join(disappeared),
        "testapp_pod_node_changes_count": len(node_changes),
        "testapp_pod_node_changes": " | ".join(node_changes),
        "testapp_pod_problem_after_count": len(status_problem_after),
        "testapp_pod_problem_after": " | ".join(status_problem_after),
        "pod_problem_word_matches_before_after_total": pod_problem_count_text,
    }


def classify_self_healing(pod_info: Dict, node_info: Dict, event_info: Dict) -> Tuple[str, str]:
    workload_healing = []
    node_related = []

    if pod_info["testapp_pod_restart_delta"] > 0:
        workload_healing.append("testapp_restart_delta")
    if pod_info["testapp_pods_new_after_count"] > 0 or pod_info["testapp_pods_disappeared_count"] > 0:
        workload_healing.append("testapp_pod_recreated")
    if pod_info["testapp_pod_node_changes_count"] > 0:
        workload_healing.append("testapp_rescheduled")

    if event_info["node_notready_new_events"] > 0:
        node_related.append("new_NodeNotReady_event")
    if event_info["node_notreachable_new_events"] > 0:
        node_related.append("new_NodeNotReachable_event")
    if node_info["node_status_changed_count"] > 0:
        node_related.append("node_status_changed_snapshot")

    if workload_healing:
        return "yes_workload_healing", " | ".join(workload_healing + node_related)

    if node_related:
        return "node_reachability_event_only", " | ".join(node_related)

    return "no", ""


def phase_row(scenario: str, run: str, phase_name: str, phase: Dict) -> Dict:
    return {
        "scenario": scenario,
        "run": run,
        "phase": phase_name,
        "requests_total": to_int(phase.get("requests_total")),
        "success": to_int(phase.get("success")),
        "failed": to_int(phase.get("failed")),
        "success_rate_percent": to_float(phase.get("success_rate")),
        "error_rate_percent": to_float(phase.get("error_rate")),
        "avg_ms": to_float(phase.get("avg_ms")),
        "median_ms": to_float(phase.get("median_ms")),
        "p95_ms": to_float(phase.get("p95_ms")),
        "p99_ms": to_float(phase.get("p99_ms")),
        "min_ms": to_float(phase.get("min_ms")),
        "max_ms": to_float(phase.get("max_ms")),
        "outliers_gt_10s": to_int(phase.get("outliers_gt_10s")),
    }


def write_csv(path: Path, rows: List[Dict]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def vals(rows: List[Dict], key: str) -> List[float]:
    out = []
    for r in rows:
        v = r.get(key)
        if isinstance(v, (int, float)) and v is not None:
            out.append(float(v))
    return out


def mean(v: List[float]) -> Optional[float]:
    return statistics.mean(v) if v else None


def stdev(v: List[float]) -> Optional[float]:
    if not v:
        return None
    if len(v) == 1:
        return 0.0
    return statistics.stdev(v)


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


per_phase_rows = []
per_run_rows = []

for scenario in FINAL_SCENARIOS:
    scenario_dir = BASE / scenario
    run_dirs = sorted(
        [p for p in scenario_dir.iterdir() if p.is_dir() and re.match(r"^run-\d+", p.name)]
    )

    for run_dir in run_dirs:
        summary_path = run_dir / "summary.txt"
        if not summary_path.exists():
            raise FileNotFoundError(f"Missing summary: {summary_path}")

        summary = parse_summary(summary_path)

        for phase_name in ["overall", "baseline", "fault", "after"]:
            per_phase_rows.append(
                phase_row(scenario, run_dir.name, phase_name, summary.get(phase_name, {}))
            )

        fault = summary.get("fault", {})
        after = summary.get("after", {})
        recovery = summary.get("recovery", {})
        validation = summary.get("validation", {})

        event_info = event_diff(run_dir)
        node_info = node_status_analysis(run_dir)
        pod_info = pod_analysis(run_dir)

        self_healing, self_healing_reason = classify_self_healing(pod_info, node_info, event_info)

        fault_requests = to_int(fault.get("requests_total"))
        valid_fault_metrics = (
            fault_requests is not None
            and fault_requests > 0
            and to_float(fault.get("success_rate")) is not None
            and to_float(fault.get("error_rate")) is not None
        )

        after_requests = to_int(after.get("requests_total"))
        recovery_s = to_float(recovery.get("recovery_latency_s"))
        recovery_observed = recovery_s is not None and after_requests is not None and after_requests > 0

        if valid_fault_metrics:
            validity_note = "valid"
        elif scenario == "link-cut-1s":
            validity_note = "kein_requeststart_im_1s_faultfenster"
        else:
            validity_note = "keine_fault_requests"

        if recovery_observed:
            recovery_note = "observed"
        elif after_requests == 0:
            recovery_note = "not_observed_after_requests_0"
        else:
            recovery_note = "not_observed"

        final_cluster_stable = (
            node_info["node_final_all_ready"]
            and pod_info["testapp_pod_problem_after_count"] == 0
            and pod_info["testapp_pods_after_count"] >= 3
        )

        if final_cluster_stable and event_info["node_notready_new_events"] == 0 and node_info["node_status_changed_count"] == 0:
            stabilization_observed = True
            stabilization_time_s = 0.0
            stabilization_note = "stable_in_before_after_snapshots_no_new_node_event"
        elif final_cluster_stable:
            stabilization_observed = True
            stabilization_time_s = None
            stabilization_note = "final_snapshot_stable_duration_not_quantifiable_from_snapshots"
        else:
            stabilization_observed = False
            stabilization_time_s = None
            stabilization_note = "final_snapshot_not_stable_or_incomplete"

        per_run_rows.append({
            "scenario": scenario,
            "run": run_dir.name,

            "fault_requests_total": fault_requests,
            "valid_for_fault_metrics": valid_fault_metrics,
            "validity_note": validity_note,

            "fault_success": to_int(fault.get("success")),
            "fault_failed": to_int(fault.get("failed")),
            "fault_success_rate_percent": to_float(fault.get("success_rate")),
            "fault_error_rate_percent": to_float(fault.get("error_rate")),

            "fault_avg_ms": to_float(fault.get("avg_ms")),
            "fault_median_ms": to_float(fault.get("median_ms")),
            "fault_p95_ms": to_float(fault.get("p95_ms")),
            "fault_p99_ms": to_float(fault.get("p99_ms")),
            "fault_min_ms": to_float(fault.get("min_ms")),
            "fault_max_ms": to_float(fault.get("max_ms")),
            "fault_outliers_gt_10s": to_int(fault.get("outliers_gt_10s")),

            "after_requests_total": after_requests,
            "recovery_time_s": recovery_s,
            "recovery_observed": recovery_observed,
            "recovery_note": recovery_note,

            "cluster_stabilization_observed": stabilization_observed,
            "cluster_stabilization_time_s": stabilization_time_s,
            "cluster_stabilization_note": stabilization_note,

            **pod_info,
            **node_info,
            **event_info,

            "self_healing_classification": self_healing,
            "self_healing_reason": self_healing_reason,

            "router_path_valid": validation.get("router_path_valid", ""),
            "fault_applied": validation.get("fault_applied", ""),
        })


per_run_rows.sort(key=lambda r: (SCENARIO_ORDER[r["scenario"]], r["run"]))
per_phase_rows.sort(key=lambda r: (SCENARIO_ORDER[r["scenario"]], r["run"], r["phase"]))

write_csv(OUT_DIR / "k3s_link_cut_per_phase_final.csv", per_phase_rows)
write_csv(OUT_DIR / "k3s_link_cut_per_run_final.csv", per_run_rows)

summary_rows = []

for scenario in FINAL_SCENARIOS:
    rows_total = [r for r in per_run_rows if r["scenario"] == scenario]
    rows_valid = [r for r in rows_total if r["valid_for_fault_metrics"]]
    rows_recovery = [r for r in rows_total if r["recovery_observed"]]

    success = vals(rows_valid, "fault_success_rate_percent")
    error = vals(rows_valid, "fault_error_rate_percent")
    recovery_vals = vals(rows_recovery, "recovery_time_s")

    summary_rows.append({
        "scenario": scenario,
        "runs_total": len(rows_total),
        "runs_valid_for_fault_metrics": len(rows_valid),
        "runs_invalid_fault_requests_0": len(rows_total) - len(rows_valid),

        "fault_success_rate_mean_percent": mean(success),
        "fault_success_rate_std_percent": stdev(success),
        "fault_success_rate_min_percent": min(success) if success else None,
        "fault_success_rate_max_percent": max(success) if success else None,

        "fault_error_rate_mean_percent": mean(error),
        "fault_error_rate_std_percent": stdev(error),

        "recovery_observed_runs": len(rows_recovery),
        "recovery_unobserved_runs": len(rows_total) - len(rows_recovery),
        "recovery_time_s_mean_observed_only": mean(recovery_vals),
        "recovery_time_s_std_observed_only": stdev(recovery_vals),
        "recovery_time_s_min_observed_only": min(recovery_vals) if recovery_vals else None,
        "recovery_time_s_max_observed_only": max(recovery_vals) if recovery_vals else None,

        "cluster_stable_final_snapshot_runs": sum(1 for r in rows_total if r["cluster_stabilization_observed"]),
        "cluster_stabilization_time_quantifiable_runs": sum(1 for r in rows_total if r["cluster_stabilization_time_s"] is not None),

        "testapp_pod_restart_delta_total": sum(r["testapp_pod_restart_delta"] for r in rows_total),
        "testapp_pod_restart_runs": sum(1 for r in rows_total if r["testapp_pod_restart_delta"] > 0),
        "testapp_pod_recreated_runs": sum(1 for r in rows_total if r["testapp_pods_new_after_count"] > 0 or r["testapp_pods_disappeared_count"] > 0),
        "testapp_pod_rescheduled_runs": sum(1 for r in rows_total if r["testapp_pod_node_changes_count"] > 0),

        "node_notready_new_event_runs": sum(1 for r in rows_total if r["node_notready_new_events"] > 0),
        "node_notready_new_events_total": sum(r["node_notready_new_events"] for r in rows_total),
        "node_notreachable_new_event_runs": sum(1 for r in rows_total if r["node_notreachable_new_events"] > 0),
        "node_final_not_all_ready_runs": sum(1 for r in rows_total if not r["node_final_all_ready"]),

        "self_healing_workload_runs": sum(1 for r in rows_total if r["self_healing_classification"] == "yes_workload_healing"),
        "node_reachability_event_only_runs": sum(1 for r in rows_total if r["self_healing_classification"] == "node_reachability_event_only"),
    })

write_csv(OUT_DIR / "k3s_link_cut_summary_final.csv", summary_rows)

with (OUT_DIR / "k3s_link_cut_appendix_requests_final.tex").open("w", encoding="utf-8") as f:
    f.write("% Automatically generated final compact request/recovery appendix table\n")
    f.write(r"\begin{longtable}{llrrrrrrrl}" + "\n")
    f.write(r"\caption{Einzelwerte der K3s-Verbindungsabbrüche: Request- und Recovery-Metriken}\label{tab:appendix-k3s-link-cut-requests}\\" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Dauer & Run & Req. & OK & Fail & Succ. [\%] & Err. [\%] & Rec. [s] & gültig & Status \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endfirsthead" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Dauer & Run & Req. & OK & Fail & Succ. [\%] & Err. [\%] & Rec. [s] & gültig & Status \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endhead" + "\n")

    for r in per_run_rows:
        status = {
            "valid": "ok",
            "kein_requeststart_im_1s_faultfenster": "kein Req.-Start im Fault",
            "keine_fault_requests": "keine Fault-Req.",
        }.get(r["validity_note"], r["validity_note"])

        f.write(
            f"{SCENARIO_LABELS[r['scenario']]} & "
            f"{esc(short_run(r['run']))} & "
            f"{de(r['fault_requests_total'])} & "
            f"{de(r['fault_success'])} & "
            f"{de(r['fault_failed'])} & "
            f"{de(r['fault_success_rate_percent'])} & "
            f"{de(r['fault_error_rate_percent'])} & "
            f"{de(r['recovery_time_s'])} & "
            f"{de(r['valid_for_fault_metrics'])} & "
            f"{esc(status)} \\\\\n"
        )

    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{longtable}" + "\n")

with (OUT_DIR / "k3s_link_cut_appendix_cluster_final.tex").open("w", encoding="utf-8") as f:
    f.write("% Automatically generated final compact cluster/self-healing appendix table\n")
    f.write(r"\begin{longtable}{llrrrrrll}" + "\n")
    f.write(r"\caption{Einzelwerte der K3s-Verbindungsabbrüche: Clusterzustand und Self-Healing-Metriken}\label{tab:appendix-k3s-link-cut-cluster}\\" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Dauer & Run & Pod-Rest. & Pod neu & Pod weg & Resched. & NodeNotReady & Final Ready & Self-Healing \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endfirsthead" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Dauer & Run & Pod-Rest. & Pod neu & Pod weg & Resched. & NodeNotReady & Final Ready & Self-Healing \\" + "\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endhead" + "\n")

    for r in per_run_rows:
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

print("Wrote final link-cut analysis files:")
print(OUT_DIR / "k3s_link_cut_per_phase_final.csv")
print(OUT_DIR / "k3s_link_cut_per_run_final.csv")
print(OUT_DIR / "k3s_link_cut_summary_final.csv")
print(OUT_DIR / "k3s_link_cut_appendix_requests_final.tex")
print(OUT_DIR / "k3s_link_cut_appendix_cluster_final.tex")
