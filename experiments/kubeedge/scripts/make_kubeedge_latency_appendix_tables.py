from pathlib import Path
import csv
import statistics
from datetime import datetime, timedelta, timezone

BASE = Path("experiments/kubeedge/latency-tests")
ANALYSIS = BASE / "analysis"
ANALYSIS.mkdir(parents=True, exist_ok=True)

SCENARIOS = [
    ("1s", BASE / "latency-1s-async-limited"),
    ("1min", BASE / "latency-1min-async-limited"),
    ("10min", BASE / "latency-10min-async-limited"),
    ("30min", BASE / "latency-30min-async-limited"),
]

REQ_OUT = ANALYSIS / "kubeedge_latency_appendix_requests_recovery_final.tex"
CLUSTER_OUT = ANALYSIS / "kubeedge_latency_appendix_cluster_self_healing_final.tex"

REQ_CSV_OUT = ANALYSIS / "kubeedge_latency_appendix_requests_recovery_final.csv"
CLUSTER_CSV_OUT = ANALYSIS / "kubeedge_latency_appendix_cluster_self_healing_final.csv"

EXISTING_CLUSTER_CSV = ANALYSIS / "kubeedge_latency_cluster_self_healing_per_run_final.csv"
EXISTING_REQUEST_CSV = ANALYSIS / "kubeedge_latency_requests_recovery_per_run_final.csv"


def parse_time(value):
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace").strip()


def to_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.upper() == "NA" or value.lower() == "none":
        return None
    return float(value.replace("%", "").replace(",", "."))


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


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * (p / 100)
    lower = int(k)
    upper = min(lower + 1, len(values) - 1)
    weight = k - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def truthy(value):
    return str(value).strip().lower() in {"true", "yes", "1", "ja"}


def count_node_notready_events(run_dir):
    before = run_dir / "events_before.txt"
    after = run_dir / "events_after.txt"

    if not after.exists():
        return None

    before_count = 0
    if before.exists():
        before_lines = before.read_text(encoding="utf-8", errors="replace").splitlines()
        before_count = sum(1 for line in before_lines if "NodeNotReady" in line)

    after_lines = after.read_text(encoding="utf-8", errors="replace").splitlines()
    after_count = sum(1 for line in after_lines if "NodeNotReady" in line)

    return max(after_count - before_count, 0)


def load_existing_request_metrics():
    data = {}
    if not EXISTING_REQUEST_CSV.exists():
        return data
    with EXISTING_REQUEST_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["scenario"], row["run"])
            data[key] = row
    return data


def load_existing_cluster_metrics():
    data = {}
    if not EXISTING_CLUSTER_CSV.exists():
        return data
    with EXISTING_CLUSTER_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["scenario"], row["run"])
            data[key] = row
    return data


existing_request = load_existing_request_metrics()
existing_cluster = load_existing_cluster_metrics()

request_rows = []
cluster_rows = []

for scenario, scenario_dir in SCENARIOS:
    for run_dir in sorted(scenario_dir.glob("run-*-router")):
        run = run_dir.name.replace("-router", "")

        requests_path = run_dir / "requests.csv"
        fault_time_path = run_dir / "fault_time.txt"
        duration_path = run_dir / "duration_seconds.txt"

        if not requests_path.exists():
            raise FileNotFoundError(f"Missing requests.csv: {requests_path}")
        if not fault_time_path.exists():
            raise FileNotFoundError(f"Missing fault_time.txt: {fault_time_path}")
        if not duration_path.exists():
            raise FileNotFoundError(f"Missing duration_seconds.txt: {duration_path}")

        fault_start = parse_time(read_text(fault_time_path))
        duration_s = float(read_text(duration_path))
        fault_end = fault_start + timedelta(seconds=duration_s)

        fault_durations = []
        fault_success = 0
        fault_fail = 0

        with requests_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                start_raw = (
                    row.get("request_start_time")
                    or row.get("timestamp")
                    or row.get("start_time")
                )
                if not start_raw:
                    continue

                start = parse_time(start_raw)

                if fault_start <= start < fault_end:
                    success_raw = str(row.get("success", "")).strip().lower()
                    is_success = success_raw in {"true", "1", "yes"}

                    duration_raw = (
                        row.get("duration_ms")
                        or row.get("response_time_ms")
                        or row.get("latency_ms")
                    )
                    duration = to_float(duration_raw)

                    if duration is not None:
                        fault_durations.append(duration)

                    if is_success:
                        fault_success += 1
                    else:
                        fault_fail += 1

        req_total = fault_success + fault_fail
        success_rate = (fault_success / req_total * 100) if req_total else None
        error_rate = (fault_fail / req_total * 100) if req_total else None
        median_ms = statistics.median(fault_durations) if fault_durations else None
        p95_ms = percentile(fault_durations, 95)

        recovery = to_float(
            existing_request.get((scenario, run), {}).get("recovery_latency_s")
        )

        request_rows.append({
            "scenario": scenario,
            "run": run,
            "req": req_total,
            "ok": fault_success,
            "fail": fault_fail,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "median_ms": median_ms,
            "p95_ms": p95_ms,
            "recovery_s": recovery,
        })

        cluster = existing_cluster.get((scenario, run), {})

        pod_restart = to_float(cluster.get("container_restart_delta")) or 0
        pod_new = to_float(cluster.get("new_testapp_pods")) or 0
        pod_removed = to_float(cluster.get("removed_testapp_pods")) or 0
        pod_replacement = truthy(cluster.get("pod_replacement"))
        node_notready = count_node_notready_events(run_dir)
        if node_notready is None:
            node_notready = to_float(cluster.get("node_notready_event_lines"))
        final_ready = truthy(cluster.get("all_nodes_after_ready"))

        # Self-Healing hier bewusst als Workload-/Reconciliation-Aktion:
        # Bei 1s gab es keine Pod-Ersetzungen/Restarts, daher "nein".
        # Ab 1min gab es Pod-Ersetzungen, daher "ja".
        self_healing = pod_replacement or pod_restart > 0

        cluster_rows.append({
            "scenario": scenario,
            "run": run,
            "pod_restart": pod_restart,
            "pod_new": pod_new,
            "pod_removed": pod_removed,
            "rescheduled": "ja" if pod_replacement else "nein",
            "node_notready": node_notready,
            "final_ready": "ja" if final_ready else "nein",
            "self_healing": "ja" if self_healing else "nein",
        })


with REQ_CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "scenario", "run", "req", "ok", "fail",
            "success_rate", "error_rate",
            "median_ms", "p95_ms", "recovery_s",
        ],
    )
    writer.writeheader()
    writer.writerows(request_rows)


with CLUSTER_CSV_OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "scenario", "run", "pod_restart", "pod_new", "pod_removed",
            "rescheduled", "node_notready", "final_ready", "self_healing",
        ],
    )
    writer.writeheader()
    writer.writerows(cluster_rows)


with REQ_OUT.open("w", encoding="utf-8") as f:
    f.write("% Automatically generated compact request/recovery appendix table\n")
    f.write(r"\begin{longtable}{llrrrrrrrr}" + "\n")
    f.write(r"\caption{Einzelwerte der KubeEdge-Latenztests: Request- und Recovery-Metriken}\label{tab:appendix-kubeedge-latency-requests}\\")
    f.write("\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Szen. & Run & Req. & OK & Fail & Succ. [\%] & Err. [\%] & Med. [ms] & p95 [ms] & Rec. [s] \\")
    f.write("\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endfirsthead" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Szen. & Run & Req. & OK & Fail & Succ. [\%] & Err. [\%] & Med. [ms] & p95 [ms] & Rec. [s] \\")
    f.write("\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endhead" + "\n")

    for r in request_rows:
        f.write(
            f"{tex_escape(r['scenario'])} & "
            f"{tex_escape(r['run'].replace('run-', 'r'))} & "
            f"{int(r['req'])} & "
            f"{int(r['ok'])} & "
            f"{int(r['fail'])} & "
            f"{fmt_de(r['success_rate'], 2)} & "
            f"{fmt_de(r['error_rate'], 2)} & "
            f"{fmt_de(r['median_ms'], 2)} & "
            f"{fmt_de(r['p95_ms'], 2)} & "
            f"{fmt_de(r['recovery_s'], 2)} \\\\\n"
        )

    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{longtable}" + "\n")


with CLUSTER_OUT.open("w", encoding="utf-8") as f:
    f.write("% Automatically generated compact cluster/self-healing appendix table\n")
    f.write(r"\begin{longtable}{llrrrrrll}" + "\n")
    f.write(r"\caption{Einzelwerte der KubeEdge-Latenztests: Clusterzustand und Self-Healing-Metriken}\label{tab:appendix-kubeedge-latency-cluster}\\")
    f.write("\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Szen. & Run & Pod-Rest. & Pod neu & Pod weg & Resched. & NodeNotReady & Final Ready & Self-Healing \\")
    f.write("\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endfirsthead" + "\n")
    f.write(r"\toprule" + "\n")
    f.write(r"Szen. & Run & Pod-Rest. & Pod neu & Pod weg & Resched. & NodeNotReady & Final Ready & Self-Healing \\")
    f.write("\n")
    f.write(r"\midrule" + "\n")
    f.write(r"\endhead" + "\n")

    for r in cluster_rows:
        f.write(
            f"{tex_escape(r['scenario'])} & "
            f"{tex_escape(r['run'].replace('run-', 'r'))} & "
            f"{fmt_de(r['pod_restart'], 0)} & "
            f"{fmt_de(r['pod_new'], 0)} & "
            f"{fmt_de(r['pod_removed'], 0)} & "
            f"{tex_escape(r['rescheduled'])} & "
            f"{fmt_de(r['node_notready'], 0)} & "
            f"{tex_escape(r['final_ready'])} & "
            f"{tex_escape(r['self_healing'])} \\\\\n"
        )

    f.write(r"\bottomrule" + "\n")
    f.write(r"\end{longtable}" + "\n")


print("Wrote:")
print(REQ_OUT)
print(CLUSTER_OUT)
print(REQ_CSV_OUT)
print(CLUSTER_CSV_OUT)
