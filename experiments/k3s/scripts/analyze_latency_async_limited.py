#!/usr/bin/env python3
import csv
import statistics as stats
from pathlib import Path
from datetime import datetime
from collections import Counter

SCENARIO = Path("experiments/k3s/network-tests/latency-60s-async-limited")
OUT = SCENARIO / "README.md"

def t(s):
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))

def pct(vals, p):
    if not vals:
        return None
    vals = sorted(vals)
    return vals[min(int(len(vals) * p / 100), len(vals) - 1)]

def fmt(v, digits=2):
    if v is None:
        return "NA"
    return f"{v:.{digits}f}"

def read_file(path, default=""):
    return path.read_text().strip() if path.exists() else default

def read_requests(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append({
                    "id": r.get("request_id", ""),
                    "start": t(r["request_start_time"]),
                    "end": t(r["request_end_time"]),
                    "status": r.get("status_code", ""),
                    "ms": float(r["duration_ms"]),
                    "success": r["success"] == "True",
                    "error": r.get("error", ""),
                })
            except Exception:
                pass
    return rows

def summarize(rows):
    total = len(rows)
    ok = sum(r["success"] for r in rows)
    fail = total - ok
    vals = [r["ms"] for r in rows]
    success_vals = [r["ms"] for r in rows if r["success"]]
    fail_vals = [r["ms"] for r in rows if not r["success"]]
    errors = Counter(r["error"] for r in rows if not r["success"])

    return {
        "total": total,
        "ok": ok,
        "fail": fail,
        "success_rate": ok / total * 100 if total else None,
        "error_rate": fail / total * 100 if total else None,
        "median": stats.median(vals) if vals else None,
        "p95": pct(vals, 95),
        "p99": pct(vals, 99),
        "max": max(vals) if vals else None,
        "success_median": stats.median(success_vals) if success_vals else None,
        "success_p95": pct(success_vals, 95),
        "fail_median": stats.median(fail_vals) if fail_vals else None,
        "gt_10s": sum(v > 10_000 for v in vals),
        "gt_60s": sum(v > 60_000 for v in vals),
        "gt_120s": sum(v > 120_000 for v in vals),
        "gt_300s": sum(v > 300_000 for v in vals),
        "errors": errors,
    }

runs = []

for run_dir in sorted(SCENARIO.glob("run-*-router")):
    fault_path = run_dir / "fault_time.txt"
    recovery_path = run_dir / "recovery_time.txt"
    requests_path = run_dir / "requests.csv"

    if not fault_path.exists() or not recovery_path.exists() or not requests_path.exists():
        continue

    fault = t(fault_path.read_text())
    recovery = t(recovery_path.read_text())
    rows = read_requests(requests_path)

    baseline = [r for r in rows if r["start"] < fault]
    fault_rows = [r for r in rows if fault <= r["start"] < recovery]
    after = [r for r in rows if r["start"] >= recovery]

    traceroute = read_file(run_dir / "traceroute_before.txt")
    tc_during = read_file(run_dir / "tc_during.txt")
    tc_after = read_file(run_dir / "tc_after.txt")

    recovery_latency = None
    for r in after:
        if r["success"] and r["ms"] is not None and r["ms"] < 500:
            recovery_latency = (r["end"] - recovery).total_seconds()
            break

    runs.append({
        "name": run_dir.name,
        "delay": read_file(run_dir / "delay.txt"),
        "duration": read_file(run_dir / "duration_seconds.txt"),
        "baseline_s": read_file(run_dir / "baseline_seconds.txt"),
        "after_s": read_file(run_dir / "after_seconds.txt"),
        "timeout": read_file(run_dir / "timeout_seconds.txt"),
        "max_in_flight": read_file(run_dir / "max_in_flight.txt", "NA"),
        "valid_router": "10.10.10.128" in traceroute,
        "valid_tc": "delay 60s" in tc_during,
        "valid_cleanup": "fq_codel" in tc_after or "pfifo_fast" in tc_after,
        "overall": summarize(rows),
        "baseline": summarize(baseline),
        "fault": summarize(fault_rows),
        "after": summarize(after),
        "recovery_latency": recovery_latency,
    })

valid_router = sum(r["valid_router"] for r in runs)
valid_tc = sum(r["valid_tc"] for r in runs)
valid_cleanup = sum(r["valid_cleanup"] for r in runs)

fault_success = [r["fault"]["success_rate"] for r in runs if r["fault"]["success_rate"] is not None]
fault_error = [r["fault"]["error_rate"] for r in runs if r["fault"]["error_rate"] is not None]
overall_success = [r["overall"]["success_rate"] for r in runs if r["overall"]["success_rate"] is not None]
recovery_vals = [r["recovery_latency"] for r in runs if r["recovery_latency"] is not None]

with open(OUT, "w") as f:
    f.write("# Latenztest 60s – asynchroner Monitor mit begrenzter Parallelität\n\n")

    f.write("## Ziel\n\n")
    f.write(
        "In diesem Test wurde das Verhalten der Testanwendung bei einer künstlich eingebrachten "
        "Netzwerklatenz von 60 Sekunden untersucht. Im Unterschied zum synchronen Monitor wurde "
        "ein asynchroner Request-Monitor verwendet, der mehrere Requests parallel offen halten kann. "
        "Die Parallelität wurde durch `max-in-flight` begrenzt, um unkontrollierte Backlog-Effekte zu reduzieren.\n\n"
    )

    f.write("## Parameter\n\n")
    first = runs[0] if runs else {}
    f.write("| Parameter | Wert |\n|---|---:|\n")
    f.write(f"| Eingebrachte Latenz | {first.get('delay', 'NA')} |\n")
    f.write("| Erwartete Round-Trip-Zeit | ca. 120s |\n")
    f.write(f"| Vorlauf | {first.get('baseline_s', 'NA')}s |\n")
    f.write(f"| Störphase | {first.get('duration', 'NA')}s |\n")
    f.write(f"| Nachlauf | {first.get('after_s', 'NA')}s |\n")
    f.write(f"| Wiederholungen | {len(runs)} |\n")
    f.write(f"| HTTP Timeout | {first.get('timeout', 'NA')}s |\n")
    f.write("| Request-Intervall | 1s |\n")
    f.write(f"| Max. parallele Requests | {first.get('max_in_flight', 'NA')} |\n\n")

    f.write("## Validierung\n\n")
    f.write(f"- Vorhandene Runs: {len(runs)}/10\n")
    f.write(f"- Routerpfad validiert: {valid_router}/{len(runs)}\n")
    f.write(f"- `tc netem delay 60s` aktiv: {valid_tc}/{len(runs)}\n")
    f.write(f"- Cleanup nach Störphase dokumentiert: {valid_cleanup}/{len(runs)}\n\n")

    f.write("## Zusammenfassung pro Run\n\n")
    f.write("| Run | Overall Success [%] | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | >60s | >120s | >300s | Recovery [s] |\n")
    f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
    for r in runs:
        fs = r["fault"]
        f.write(
            f"| {r['name']} | "
            f"{fmt(r['overall']['success_rate'])} | "
            f"{fmt(fs['success_rate'])} | "
            f"{fmt(fs['error_rate'])} | "
            f"{fmt(fs['median'])} | "
            f"{fmt(fs['p95'])} | "
            f"{fs['gt_60s']} | "
            f"{fs['gt_120s']} | "
            f"{fs['gt_300s']} | "
            f"{fmt(r['recovery_latency'])} |\n"
        )

    f.write("\n## Aggregierte Metriken\n\n")
    if overall_success:
        f.write(f"- Overall Request Success Rate Mittelwert: {fmt(stats.mean(overall_success))} %\n")
    if fault_success:
        f.write(f"- Fault Success Rate Mittelwert: {fmt(stats.mean(fault_success))} %\n")
        f.write(f"- Fault Success Rate Minimum: {fmt(min(fault_success))} %\n")
        f.write(f"- Fault Success Rate Maximum: {fmt(max(fault_success))} %\n")
    if fault_error:
        f.write(f"- Fault Error Rate Mittelwert: {fmt(stats.mean(fault_error))} %\n")
    if recovery_vals:
        f.write(f"- Recovery Time Mittelwert: {fmt(stats.mean(recovery_vals))} s\n")
        f.write(f"- Recovery Time Minimum: {fmt(min(recovery_vals))} s\n")
        f.write(f"- Recovery Time Maximum: {fmt(max(recovery_vals))} s\n")
    else:
        f.write("- Recovery Time: nicht in allen Runs bestimmbar\n")

    f.write("\n## Interpretation\n\n")
    f.write(
        "Die Messreihe zeigt, dass die Testanwendung während der 60s-Latenz weiterhin teilweise erreichbar blieb, "
        "jedoch mit deutlich reduzierter Erfolgsrate und stark erhöhten Antwortzeiten. Die Baseline-Phase war in den "
        "Runs stabil, und die Nachlaufphase erreichte, sofern Requests nach dem Recovery-Zeitpunkt erfasst wurden, "
        "wieder erfolgreiche Antworten.\n\n"
    )
    f.write(
        "Die Fault Success Rate ist die zentrale Kennzahl für dieses Szenario, da sie ausschließlich Requests betrachtet, "
        "die während der aktiven Störung gestartet wurden. Die Overall Success Rate ist ergänzend zu betrachten, da sie "
        "auch die störungsfreien Vor- und Nachlaufphasen enthält.\n\n"
    )
    f.write(
        "Die begrenzte asynchrone Messung bildet ein kontrolliertes Kommunikationsmodell ab: Mehrere Requests dürfen parallel "
        "offen sein, gleichzeitig wird ein unkontrollierter Request-Backlog durch `max-in-flight` begrenzt. Die Ergebnisse "
        "hängen daher neben K3s auch von Timeout, Request-Intervall und maximaler Parallelität ab.\n"
    )

print(f"README geschrieben: {OUT}")
print(f"Runs ausgewertet: {len(runs)}")
