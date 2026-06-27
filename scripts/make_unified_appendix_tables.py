#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]

COLUMNS = [
    "Run",
    "Störung",
    "Ziel",
    "Req.",
    "OK",
    "Fail",
    "Succ. [%]",
    "Err. [%]",
    "Rec. [s]",
    "Stab. [s]",
    "Pod-Rest.",
    "NodeNotReady",
    "NotReady [s]",
    "Final Ready",
    "gültig",
]


OUTPUTS = [
    {
        "name": "k3s_latency",
        "kind": "k3s_network",
        "input": "experiments/k3s/latency-tests/analysis/k3s_latency_per_run.csv",
        "out_dir": "experiments/k3s/latency-tests/analysis",
        "out_base": "k3s_latency_appendix_runs",
        "caption": "Einzelwerte der K3s-Latenztests pro Versuchslauf.",
        "label": "tab:appendix-k3s-latency-runs",
        "target": "server--worker",
    },
    {
        "name": "k3s_packet_loss",
        "kind": "k3s_network",
        "input": "experiments/k3s/packet-loss-tests/analysis/k3s_packet_loss_per_run_final.csv",
        "out_dir": "experiments/k3s/packet-loss-tests/analysis",
        "out_base": "k3s_packet_loss_appendix_runs",
        "caption": "Einzelwerte der K3s-Paketverlusttests pro Versuchslauf.",
        "label": "tab:appendix-k3s-packet-loss-runs",
        "target": "server--worker",
    },
    {
        "name": "k3s_link_cut",
        "kind": "k3s_network",
        "input": "experiments/k3s/link-cut-tests/analysis/k3s_link_cut_per_run_final.csv",
        "out_dir": "experiments/k3s/link-cut-tests/analysis",
        "out_base": "k3s_link_cut_appendix_runs",
        "caption": "Einzelwerte der K3s-Verbindungsabbruchtests pro Versuchslauf.",
        "label": "tab:appendix-k3s-link-cut-runs",
        "target": "server--worker",
    },
    {
        "name": "kubeedge_pod_failure",
        "kind": "kubeedge_pod_failure",
        "input": "experiments/kubeedge/pod-failure/analysis/kubeedge_pod_failure_per_run_final.csv",
        "out_dir": "experiments/kubeedge/pod-failure/analysis",
        "out_base": "kubeedge_pod_failure_appendix_runs",
        "caption": "Einzelwerte der KubeEdge-Pod-Ausfalltests pro Versuchslauf.",
        "label": "tab:appendix-kubeedge-pod-failure-runs",
    },
    {
        "name": "kubeedge_node_failure",
        "kind": "kubeedge_node_failure",
        "input": "experiments/kubeedge/node-failure/analysis/kubeedge_node_failure_per_run_final.csv",
        "out_dir": "experiments/kubeedge/node-failure/analysis",
        "out_base": "kubeedge_node_failure_appendix_runs",
        "caption": "Einzelwerte der KubeEdge-Node-Ausfalltests pro Versuchslauf.",
        "label": "tab:appendix-kubeedge-node-failure-runs",
    },
    {
        "name": "kubeedge_latency",
        "kind": "kubeedge_latency",
        "requests_input": "experiments/kubeedge/latency-tests/analysis/kubeedge_latency_requests_recovery_per_run_final.csv",
        "cluster_input": "experiments/kubeedge/latency-tests/analysis/kubeedge_latency_cluster_self_healing_per_run_final.csv",
        # Falls vorhanden, wird diese Datei bevorzugt für Req./OK/Fail verwendet.
        "appendix_requests_input": "experiments/kubeedge/latency-tests/analysis/kubeedge_latency_appendix_requests_recovery_final.csv",
        "out_dir": "experiments/kubeedge/latency-tests/analysis",
        "out_base": "kubeedge_latency_appendix_runs",
        "caption": "Einzelwerte der KubeEdge-Latenztests pro Versuchslauf.",
        "label": "tab:appendix-kubeedge-latency-runs",
        "target": "cloud--edge",
    },
    {
        "name": "kubeedge_packet_loss",
        "kind": "kubeedge_summary_glob",
        "inputs_glob": "experiments/kubeedge/packet-loss-tests/*/packet-loss-summary.csv",
        "out_dir": "experiments/kubeedge/packet-loss-tests/analysis",
        "out_base": "kubeedge_packet_loss_appendix_runs",
        "caption": "Einzelwerte der KubeEdge-Paketverlusttests pro Versuchslauf.",
        "label": "tab:appendix-kubeedge-packet-loss-runs",
        "target": "cloud--edge",
        "scenario_source": "loss",
        "scenario_prefix": "Paketverlust",
        "applied_column": "packet_loss_applied",
        "valid_columns": ["router_path_valid", "packet_loss_applied", "tc_cleanup_documented"],
    },
    {
        "name": "kubeedge_link_cut",
        "kind": "kubeedge_summary_glob",
        "inputs_glob": "experiments/kubeedge/link-cut-tests/*/link-cut-summary.csv",
        "out_dir": "experiments/kubeedge/link-cut-tests/analysis",
        "out_base": "kubeedge_link_cut_appendix_runs",
        "caption": "Einzelwerte der KubeEdge-Verbindungsabbruchtests pro Versuchslauf.",
        "label": "tab:appendix-kubeedge-link-cut-runs",
        "target": "cloud--edge",
        "scenario_source": "scenario",
        "scenario_prefix": "Link-Cut",
        "applied_column": "link_cut_applied",
        "valid_columns": ["router_path_valid", "link_cut_applied", "interface_recovered", "router_recovery_documented"],
    },
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def norm(value: object) -> str:
    if value is None:
        return "--"
    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return "--"
    return s


def first(row: Dict[str, str], names: Iterable[str], default: str = "--") -> str:
    for name in names:
        if name in row and norm(row.get(name)) != "--":
            return norm(row.get(name))
    return default


def bool_de(value: object) -> str:
    s = norm(value).lower()
    if s in {"true", "1", "yes", "ja", "y"}:
        return "ja"
    if s in {"false", "0", "no", "nein", "n"}:
        return "nein"
    return norm(value)


def fmt_num(value: object, digits: int = 2) -> str:
    s = norm(value)
    if s == "--":
        return "--"
    try:
        x = float(s)
    except ValueError:
        return s
    if x.is_integer():
        return str(int(x))
    return f"{x:.{digits}f}"


def clean_percent(value: object) -> str:
    s = norm(value)
    if s == "--":
        return "--"
    return s.replace("%", "")


def fmt_percent(value: object) -> str:
    return fmt_num(clean_percent(value), 2)




def latex_escape(s: object) -> str:
    text = norm(s)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def latex_bool(s: object) -> str:
    return latex_escape(bool_de(s))


def valid_from_row(row: Dict[str, str]) -> str:
    return bool_de(first(row, ["valid_for_fault_metrics", "valid", "gültig"], "ja"))


def scenario_label(raw: str) -> str:
    s = norm(raw)
    if s == "--":
        return "--"

    replacements = {
        "latency-1s": "Latenz 1s",
        "latency-1min": "Latenz 1min",
        "latency-10min": "Latenz 10min",
        "latency-30min": "Latenz 30min",
        "packet-loss-1pct": "Paketverlust 1%",
        "packet-loss-10pct": "Paketverlust 10%",
        "packet-loss-50pct": "Paketverlust 50%",
        "packet-loss-70pct": "Paketverlust 70%",
        "packet-loss-100pct": "Paketverlust 100%",
        "link-cut-1s": "Link-Cut 1s",
        "link-cut-1min": "Link-Cut 1min",
        "link-cut-10min": "Link-Cut 10min",
        "link-cut-30min": "Link-Cut 30min",
        "100%": "Paketverlust 100%",
        "70%": "Paketverlust 70%",
        "50%": "Paketverlust 50%",
        "10%": "Paketverlust 10%",
        "1%": "Paketverlust 1%",
        "1s": "Latenz 1s",
        "1min": "Latenz 1min",
        "10min": "Latenz 10min",
        "30min": "Latenz 30min",
    }
    if s in replacements:
        return replacements[s]

    for token, label in replacements.items():
        if token in s:
            return label

    return s


def map_k3s_network(row: Dict[str, str], target: str) -> Dict[str, str]:
    return {
        "Run": first(row, ["run"]),
        "Störung": scenario_label(first(row, ["scenario"])),
        "Ziel": target,
        "Req.": fmt_num(first(row, ["fault_requests_total"]), 0),
        "OK": fmt_num(first(row, ["fault_success"]), 0),
        "Fail": fmt_num(first(row, ["fault_failed"]), 0),
        "Succ. [%]": fmt_num(first(row, ["fault_success_rate_percent"]), 2),
        "Err. [%]": fmt_num(first(row, ["fault_error_rate_percent"]), 2),
        "Rec. [s]": fmt_num(first(row, ["recovery_time_s"]), 2),
        "Stab. [s]": fmt_num(first(row, ["cluster_stabilization_time_s"]), 2),
        "Pod-Rest.": fmt_num(first(row, ["testapp_pod_restart_delta"]), 0),
        "NodeNotReady": fmt_num(first(row, ["node_notready_new_events"]), 0),
        # Für K3s-Netzwerktests liegt meist die Anzahl der neuen Events vor, aber keine Dauer.
        "NotReady [s]": "--",
        "Final Ready": latex_bool(first(row, ["node_final_all_ready"])),
        "gültig": valid_from_row(row),
    }


def map_kubeedge_pod_failure(row: Dict[str, str]) -> Dict[str, str]:
    target_parts = []
    deleted_pod = first(row, ["deleted_pod"])
    deleted_node = first(row, ["deleted_pod_node"])
    new_node = first(row, ["new_pod_node"])

    if deleted_pod != "--":
        target_parts.append(deleted_pod)
    if deleted_node != "--":
        target_parts.append(f"{deleted_node}")
    if new_node != "--" and new_node != deleted_node:
        target_parts.append(f"neu:{new_node}")

    target = " / ".join(target_parts) if target_parts else "--"
    recovery = fmt_num(first(row, ["recovery_seconds"]), 2)

    return {
        "Run": first(row, ["run"]),
        "Störung": "Pod-Ausfall",
        "Ziel": target,
        "Req.": fmt_num(first(row, ["total_requests"]), 0),
        "OK": fmt_num(first(row, ["ok_requests"]), 0),
        "Fail": fmt_num(first(row, ["failed_requests"]), 0),
        "Succ. [%]": fmt_num(first(row, ["success_rate_percent"]), 2),
        "Err. [%]": fmt_num(first(row, ["error_rate_percent"]), 2),
        "Rec. [s]": recovery,
        # Bei Pod-Ausfall entspricht der beobachtete Recovery-Wert der Wiederherstellung der Anwendung.
        # Falls keine separate Stabilisierung gemessen wurde, bleibt diese bewusst leer.
        "Stab. [s]": "--",
        "Pod-Rest.": fmt_num(first(row, ["pod_restart_delta"]), 0),
        "NodeNotReady": "0",
        "NotReady [s]": "0",
        "Final Ready": latex_bool(first(row, ["node_final_all_ready"])),
        "gültig": "ja",
    }


def map_kubeedge_node_failure(row: Dict[str, str]) -> Dict[str, str]:
    role = first(row, ["role"])
    node = first(row, ["failed_node"])
    target = f"{role}:{node}" if role != "--" and node != "--" else node

    return {
        "Run": first(row, ["run"]),
        "Störung": "Node-Ausfall",
        "Ziel": target,
        "Req.": fmt_num(first(row, ["total_requests"]), 0),
        "OK": fmt_num(first(row, ["ok_requests"]), 0),
        "Fail": fmt_num(first(row, ["failed_requests"]), 0),
        "Succ. [%]": fmt_num(first(row, ["success_rate_percent"]), 2),
        "Err. [%]": fmt_num(first(row, ["error_rate_percent"]), 2),
        "Rec. [s]": fmt_num(first(row, ["node_recovery_seconds"]), 2),
        # Hier nutzen wir die Zeit bis Node-Recovery als Stabilisierungszeit,
        # weil der stabile Node-/Clusterzustand die zentrale Node-Failure-Beobachtung ist.
        "Stab. [s]": fmt_num(first(row, ["node_recovery_seconds"]), 2),
        "Pod-Rest.": fmt_num(first(row, ["pod_restart_delta"]), 0),
        "NodeNotReady": latex_bool(first(row, ["node_notready_detected"])),
        "NotReady [s]": fmt_num(first(row, ["node_notready_seconds"]), 2),
        "Final Ready": latex_bool(first(row, ["nodes_final_ready"])),
        "gültig": "ja",
    }


def key_scenario_run(row: Dict[str, str]) -> Tuple[str, str]:
    return (norm(row.get("scenario")), norm(row.get("run")))


def find_count_source_for_kubeedge_latency(config: Dict[str, str]) -> Dict[Tuple[str, str], Dict[str, str]]:
    """
    KubeEdge latency request/recovery per-run CSV contains success rates and recovery,
    but may not contain request counts. If the older appendix CSV with counts exists,
    use it as an optional supplement.
    """
    path = ROOT / config["appendix_requests_input"]
    rows = read_csv(path)
    out: Dict[Tuple[str, str], Dict[str, str]] = {}
    for r in rows:
        scenario = first(r, ["scenario", "Szenario", "Szen.", "Störung"])
        run = first(r, ["run", "Run"])
        out[(scenario, run)] = r
    return out


def get_counts_from_optional_latency_row(row: Dict[str, str], request_row: Dict[str, str]) -> Tuple[str, str, str]:
    # Für KubeEdge-Latenz liegen Req./OK/Fail in der alten Appendix-Request-CSV
    # mit den Spalten req, ok und fail. Falls diese optionale Zeile fehlt,
    # wird als Fallback in der Request-Per-Run-Zeile gesucht.
    source = row if row else request_row

    req = first(
        source,
        ["fault_requests_total", "requests_total", "total_requests", "req", "Req.", "Req", "requests"],
    )
    ok = first(
        source,
        ["fault_success", "ok_requests", "ok", "OK", "success_requests"],
    )
    fail = first(
        source,
        ["fault_failed", "failed_requests", "fail", "Fail", "failed", "error_requests"],
    )

    return fmt_num(req, 0), fmt_num(ok, 0), fmt_num(fail, 0)


def map_kubeedge_latency(
    request_row: Dict[str, str],
    cluster_row: Optional[Dict[str, str]],
    optional_count_row: Optional[Dict[str, str]],
    target: str,
) -> Dict[str, str]:
    cluster_row = cluster_row or {}
    optional_count_row = optional_count_row or {}

    req, ok, fail = get_counts_from_optional_latency_row(optional_count_row, request_row)

    return {
        "Run": first(request_row, ["run"]),
        "Störung": scenario_label(first(request_row, ["scenario", "delay"])),
        "Ziel": target,
        "Req.": req,
        "OK": ok,
        "Fail": fail,
        "Succ. [%]": fmt_num(first(request_row, ["fault_success_rate_percent"]), 2),
        "Err. [%]": fmt_num(first(request_row, ["fault_error_rate_percent"]), 2),
        "Rec. [s]": fmt_num(first(request_row, ["recovery_latency_s"]), 2),
        # Für KubeEdge-Latenz liegt im Cluster-CSV bisher nur stabiler Snapshot, aber keine Dauer.
        "Stab. [s]": "--",
        "Pod-Rest.": fmt_num(first(cluster_row, ["container_restart_delta"]), 0),
        "NodeNotReady": fmt_num(first(cluster_row, ["node_notready_event_lines"]), 0),
        "NotReady [s]": "--",
        "Final Ready": latex_bool(first(cluster_row, ["stable_after_snapshot", "all_nodes_after_ready"])),
        "gültig": "ja",
    }


def valid_from_columns(row: Dict[str, str], columns: Iterable[str]) -> str:
    for c in columns:
        v = first(row, [c])
        if bool_de(v) == "nein":
            return "nein"
    return "ja"


def derived_count(total: str, rate_percent: str) -> str:
    total_s = norm(total)
    rate_s = clean_percent(rate_percent)
    if total_s == "--" or rate_s == "--":
        return "--"
    try:
        total_f = float(total_s)
        rate_f = float(rate_s)
    except ValueError:
        return "--"
    return str(int(round(total_f * rate_f / 100.0)))


def map_kubeedge_summary_glob(row: Dict[str, str], config: Dict[str, str]) -> Dict[str, str]:
    scenario_raw = first(row, [config.get("scenario_source", "scenario")])
    scenario = scenario_label(scenario_raw)

    req = first(row, ["fault_requests_total"])
    ok = first(row, ["fault_success"])
    fail = first(row, ["fault_failed"])

    # KubeEdge Packet-Loss enthält in der Summary keine fault_success/fault_failed-Spalten,
    # sondern nur fault_requests_total sowie Success-/Error-Raten. Für die Appendix-Tabelle
    # werden OK/Fail daraus abgeleitet.
    if norm(ok) == "--":
        ok = derived_count(req, first(row, ["fault_success_rate"]))
    if norm(fail) == "--":
        fail = derived_count(req, first(row, ["fault_error_rate"]))

    return {
        "Run": first(row, ["run"]),
        "Störung": scenario,
        "Ziel": config.get("target", "--"),
        "Req.": fmt_num(req, 0),
        "OK": fmt_num(ok, 0),
        "Fail": fmt_num(fail, 0),
        "Succ. [%]": fmt_percent(first(row, ["fault_success_rate"])),
        "Err. [%]": fmt_percent(first(row, ["fault_error_rate"])),
        "Rec. [s]": fmt_num(first(row, ["recovery_latency_s"]), 2),
        "Stab. [s]": "--",
        "Pod-Rest.": "--",
        "NodeNotReady": "--",
        "NotReady [s]": "--",
        "Final Ready": latex_bool(first(row, ["after_preflight_ok", "interface_recovered"], "ja")),
        "gültig": valid_from_columns(row, config.get("valid_columns", [])),
    }


def rows_for_config(config: Dict[str, str]) -> List[Dict[str, str]]:
    kind = config["kind"]

    if kind == "k3s_network":
        rows = read_csv(ROOT / config["input"])
        return [map_k3s_network(r, config["target"]) for r in rows]

    if kind == "kubeedge_pod_failure":
        rows = read_csv(ROOT / config["input"])
        return [map_kubeedge_pod_failure(r) for r in rows]

    if kind == "kubeedge_node_failure":
        rows = read_csv(ROOT / config["input"])
        return [map_kubeedge_node_failure(r) for r in rows]

    if kind == "kubeedge_latency":
        requests = read_csv(ROOT / config["requests_input"])
        clusters = read_csv(ROOT / config["cluster_input"])
        cluster_by_key = {key_scenario_run(r): r for r in clusters}
        optional_counts = find_count_source_for_kubeedge_latency(config)

        out = []
        for r in requests:
            key = key_scenario_run(r)
            scenario, run = key
            count_row = optional_counts.get(key) or optional_counts.get((scenario_label(scenario), run)) or {}
            out.append(map_kubeedge_latency(r, cluster_by_key.get(key), count_row, config["target"]))
        return out

    if kind == "kubeedge_summary_glob":
        paths = sorted(ROOT.glob(config["inputs_glob"]))
        rows: List[Dict[str, str]] = []
        for path in paths:
            rows.extend(read_csv(path))
        return [map_kubeedge_summary_glob(r, config) for r in rows]

    raise ValueError(f"Unknown kind: {kind}")


def latex_table(path: Path, rows: List[Dict[str, str]], caption: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    header = " & ".join(latex_escape(c) for c in COLUMNS) + r" \\"
    align = "l l p{3.2cm} r r r r r r r r r r r r"

    lines = [
        r"\begin{sidewaystable}[p]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\resizebox{\textheight}{!}{%",
        rf"\begin{{tabular}}{{{align}}}",
        r"\toprule",
        header,
        r"\midrule",
    ]

    for row in rows:
        values = [latex_escape(row.get(c, "--")) for c in COLUMNS]
        lines.append(" & ".join(values) + r" \\")

    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            rf"\caption{{{latex_escape(caption)}}}",
            rf"\label{{{latex_escape(label)}}}",
            r"\end{sidewaystable}",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    generated = 0

    for config in OUTPUTS:
        # Prüfen, ob mindestens die primäre Eingabe vorhanden ist.
        if "input" in config and not (ROOT / config["input"]).exists():
            print(f"SKIP {config['name']}: missing {config['input']}")
            continue
        if "requests_input" in config and not (ROOT / config["requests_input"]).exists():
            print(f"SKIP {config['name']}: missing {config['requests_input']}")
            continue
        if "cluster_input" in config and not (ROOT / config["cluster_input"]).exists():
            print(f"SKIP {config['name']}: missing {config['cluster_input']}")
            continue
        if "inputs_glob" in config and not list(ROOT.glob(config["inputs_glob"])):
            print(f"SKIP {config['name']}: no matches for {config['inputs_glob']}")
            continue

        rows = rows_for_config(config)
        if not rows:
            print(f"SKIP {config['name']}: no rows")
            continue

        out_dir = ROOT / config["out_dir"]
        csv_path = out_dir / f"{config['out_base']}.csv"
        tex_path = out_dir / f"{config['out_base']}.tex"

        write_csv(csv_path, rows)
        latex_table(tex_path, rows, config["caption"], config["label"])

        print(f"OK {config['name']}: {len(rows)} rows")
        print(f"  CSV: {csv_path.relative_to(ROOT)}")
        print(f"  TEX: {tex_path.relative_to(ROOT)}")
        generated += 1

    print(f"\nGenerated {generated} appendix table set(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
