#!/usr/bin/env python3
import csv
from pathlib import Path

BASE = Path("experiments/k3s/pod-failure-rerun-final")
OUT_CSV = BASE / "k3s_pod_failure_appendix_runs.csv"
OUT_TEX = Path("appendix-tables/k3s_pod_failure_appendix_runs.tex")

HEADERS = [
    "Run", "Störung", "Ziel", "Req.", "OK", "Fail", "Succ. [%]", "Err. [%]",
    "Rec. [s]", "Stab. [s]", "Pod-Rest.", "NodeNotReady", "NotReady [s]",
    "Final Ready", "gültig"
]

def read_kv(path: Path):
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
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

def tex_escape(s):
    return str(s).replace("_", r"\_").replace("%", r"\%")

rows = []

for run_dir in sorted(BASE.glob("run-*")):
    summary_path = run_dir / "summary.txt"
    routes_path = run_dir / "routes_ok.txt"

    if not summary_path.exists():
        continue

    s = read_kv(summary_path)
    routes_ok = routes_path.exists() and routes_path.read_text(encoding="utf-8").strip() == "routes_ok=true"

    run = run_dir.name
    ziel = s.get("deleted_pod_node", "--")

    node_notready = "1" if s.get("node_notready_detected") == "true" else "0"
    valid = s.get("valid", "--")
    if not routes_ok:
        valid = "nein"

    rows.append({
        "Run": run,
        "Störung": "Pod-Ausfall",
        "Ziel": ziel,
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

with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows)

with OUT_TEX.open("w", encoding="utf-8") as f:
    f.write("% Automatically generated from experiments/k3s/pod-failure-rerun-final/run-*/summary.txt\n")
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
    f.write("\\caption{Einzelwerte der K3s-Pod-Ausfalltests pro Versuchslauf.}\n")
    f.write("\\label{tab:appendix-k3s-pod-failure-runs}\n")
    f.write("\\end{sidewaystable}\n")

print(f"Wrote {OUT_CSV}")
print(f"Wrote {OUT_TEX}")
print(f"Rows: {len(rows)}")
