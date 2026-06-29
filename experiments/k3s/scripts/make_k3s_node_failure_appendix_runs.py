#!/usr/bin/env python3
import csv
from pathlib import Path
from statistics import mean, median

BASE = Path("experiments/k3s/node-failure")
WORKER_BASE = BASE / "worker-rerun-final"
SERVER_BASE = BASE / "server-rerun-final"

OUT_CSV = BASE / "k3s_node_failure_appendix_runs.csv"
OUT_TEX = Path("appendix-tables/k3s_node_failure_appendix_runs.tex")
OUT_AGG = BASE / "k3s_node_failure_summary_aggregate.txt"

HEADERS = [
    "Run", "Störung", "Ziel", "Req.", "OK", "Fail", "Succ. [%]", "Err. [%]",
    "Rec. [s]", "Stab. [s]", "Pod-Rest.", "NodeNotReady", "NotReady [s]",
    "Final Ready", "gültig"
]

def read_kv(path: Path):
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data

def fmt_num(v):
    if v in ("", None):
        return "--"
    try:
        f = float(v)
        if f.is_integer():
            return str(int(f))
        return f"{f:.2f}".rstrip("0").rstrip(".")
    except Exception:
        return str(v)

def to_float(v):
    try:
        if v in ("", None, "--"):
            return None
        return float(v)
    except Exception:
        return None

def tex_escape(s):
    return (
        str(s)
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("&", r"\&")
        .replace("#", r"\#")
    )

def collect_runs(base: Path, störung: str):
    rows = []
    for run_dir in sorted(base.glob("run-[0-9][0-9]-k3s-*")):
        if not run_dir.is_dir():
            continue

        s = read_kv(run_dir / "summary.txt")
        if not s:
            continue

        pre_ok = s.get("preflight_before_ok", "false") == "true"
        post_ok = s.get("preflight_after_ok", "false") == "true"
        valid = s.get("valid", "--")
        if not (pre_ok and post_ok):
            valid = "nein"

        node_notready = "1" if s.get("node_notready_detected") == "true" else "0"

        rows.append({
            "Run": run_dir.name,
            "Störung": störung,
            "Ziel": s.get("failed_node", "--"),
            "Req.": s.get("total_requests", "--"),
            "OK": s.get("ok_requests", "--"),
            "Fail": s.get("failed_requests", "--"),
            "Succ. [%]": fmt_num(s.get("success_rate_percent", "--")),
            "Err. [%]": fmt_num(s.get("error_rate_percent", "--")),
            "Rec. [s]": fmt_num(s.get("recovery_seconds", "--")),
            "Stab. [s]": fmt_num(s.get("stabilization_seconds", "--")),
            "Pod-Rest.": s.get("pod_restart_delta", "--"),
            "NodeNotReady": node_notready,
            "NotReady [s]": fmt_num(s.get("node_notready_seconds", "--")),
            "Final Ready": s.get("final_ready", "--"),
            "gültig": valid,
        })
    return rows

rows = []
rows.extend(collect_runs(WORKER_BASE, "Worker-Node-Ausfall"))
rows.extend(collect_runs(SERVER_BASE, "Server-Node-Ausfall"))

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
OUT_TEX.parent.mkdir(parents=True, exist_ok=True)

with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows)

with OUT_TEX.open("w", encoding="utf-8") as f:
    f.write("% Automatically generated from experiments/k3s/node-failure/*-rerun-final/run-*/summary.txt\n")
    f.write("\\begin{sidewaystable}[p]\n")
    f.write("\\centering\n")
    f.write("\\scriptsize\n")
    f.write("\\setlength{\\tabcolsep}{3pt}\n")
    f.write("\\renewcommand{\\arraystretch}{1.08}\n")
    f.write("\\resizebox{\\textheight}{!}{%\n")
    f.write("\\begin{tabular}{l l l r r r r r r r r r r l l}\n")
    f.write("\\toprule\n")
    f.write("Run & Störung & Ziel & Req. & OK & Fail & Succ. [\\%] & Err. [\\%] & Rec. [s] & Stab. [s] & Pod-Rest. & NodeNotReady & NotReady [s] & Final Ready & gültig \\\\\n")
    f.write("\\midrule\n")

    for r in rows:
        f.write(
            f"{tex_escape(r['Run'])} & "
            f"{tex_escape(r['Störung'])} & "
            f"{tex_escape(r['Ziel'])} & "
            f"{r['Req.']} & {r['OK']} & {r['Fail']} & "
            f"{r['Succ. [%]']} & {r['Err. [%]']} & "
            f"{r['Rec. [s]']} & {r['Stab. [s]']} & "
            f"{r['Pod-Rest.']} & {r['NodeNotReady']} & {r['NotReady [s]']} & "
            f"{tex_escape(r['Final Ready'])} & {tex_escape(r['gültig'])} \\\\\n"
        )

    f.write("\\bottomrule\n")
    f.write("\\end{tabular}%\n")
    f.write("}\n")
    f.write("\\caption{Einzelwerte der K3s-Node-Ausfalltests pro Versuchslauf.}\n")
    f.write("\\label{tab:appendix-k3s-node-failure-runs}\n")
    f.write("\\end{sidewaystable}\n")

def numeric(rows, key):
    values = []
    for r in rows:
        v = to_float(r.get(key))
        if v is not None:
            values.append(v)
    return values

def agg_for(name, subset):
    lines = []
    rec = numeric(subset, "Rec. [s]")
    stab = numeric(subset, "Stab. [s]")
    succ = numeric(subset, "Succ. [%]")
    err = numeric(subset, "Err. [%]")
    fail = sum(int(float(r["Fail"])) for r in subset if r["Fail"] not in ("", "--"))
    restarts = sum(int(float(r["Pod-Rest."])) for r in subset if r["Pod-Rest."] not in ("", "--"))
    valid = sum(1 for r in subset if r["gültig"] == "ja")

    lines.append(f"[{name}]")
    lines.append(f"runs={len(subset)}")
    lines.append(f"valid={valid}/{len(subset)}")
    lines.append(f"failed_requests_total={fail}")
    lines.append(f"pod_restart_delta_sum={restarts}")
    if succ:
        lines.append(f"success_rate_min={min(succ):.2f}")
        lines.append(f"success_rate_mean={mean(succ):.2f}")
        lines.append(f"success_rate_median={median(succ):.2f}")
    if err:
        lines.append(f"error_rate_max={max(err):.2f}")
        lines.append(f"error_rate_mean={mean(err):.2f}")
    if rec:
        lines.append(f"recovery_seconds_min={min(rec):.2f}")
        lines.append(f"recovery_seconds_median={median(rec):.2f}")
        lines.append(f"recovery_seconds_mean={mean(rec):.2f}")
        lines.append(f"recovery_seconds_max={max(rec):.2f}")
    if stab:
        lines.append(f"stabilization_seconds_min={min(stab):.2f}")
        lines.append(f"stabilization_seconds_median={median(stab):.2f}")
        lines.append(f"stabilization_seconds_mean={mean(stab):.2f}")
        lines.append(f"stabilization_seconds_max={max(stab):.2f}")
    lines.append("")
    return lines

worker_rows = [r for r in rows if r["Störung"] == "Worker-Node-Ausfall"]
server_rows = [r for r in rows if r["Störung"] == "Server-Node-Ausfall"]

agg_lines = []
agg_lines.append("# K3s Node Failure Aggregate")
agg_lines.append("")
agg_lines.extend(agg_for("worker", worker_rows))
agg_lines.extend(agg_for("server", server_rows))
agg_lines.extend(agg_for("combined", rows))

OUT_AGG.write_text("\n".join(agg_lines), encoding="utf-8")

print(f"Wrote {OUT_CSV}")
print(f"Wrote {OUT_TEX}")
print(f"Wrote {OUT_AGG}")
print(f"Rows: {len(rows)}")
print(f"Worker rows: {len(worker_rows)}")
print(f"Server rows: {len(server_rows)}")
