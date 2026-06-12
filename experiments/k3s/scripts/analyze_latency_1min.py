#!/usr/bin/env python3
import csv
from pathlib import Path
from datetime import datetime
from collections import Counter
import statistics as stats

SCENARIO = Path("experiments/k3s/latency-tests/latency-1min-short")
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

def read_requests(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append({
                    "start": t(r["request_start_time"]),
                    "end": t(r["request_end_time"]),
                    "status": r["status_code"],
                    "ms": float(r["duration_ms"]),
                    "success": r["success"] == "True",
                    "error": r["error"],
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
    errors = Counter(r["error"] for r in rows if not r["success"])

    return {
        "total": total,
        "ok": ok,
        "fail": fail,
        "success_rate": ok / total * 100 if total else 0,
        "error_rate": fail / total * 100 if total else 0,
        "median": stats.median(vals) if vals else None,
        "p95": pct(vals, 95),
        "p99": pct(vals, 99),
        "max": max(vals) if vals else None,
        "success_median": stats.median(success_vals) if success_vals else None,
        "success_p95": pct(success_vals, 95),
        "gt_10s": sum(v > 10_000 for v in vals),
        "gt_60s": sum(v > 60_000 for v in vals),
        "gt_120s": sum(v > 120_000 for v in vals),
        "errors": errors,
    }

runs = []

for run_dir in sorted(SCENARIO.glob("run-*-router")):
    fault = t((run_dir / "fault_time.txt").read_text())
    recovery = t((run_dir / "recovery_time.txt").read_text())
    rows = read_requests(run_dir / "requests.csv")

    baseline = [r for r in rows if r["start"] < fault]
    fault_rows = [r for r in rows if fault <= r["start"] < recovery]
    after = [r for r in rows if r["start"] >= recovery]

    summary = (run_dir / "summary.txt").read_text()
    traceroute = (run_dir / "traceroute_before.txt").read_text()
    tc_during = (run_dir / "tc_during.txt").read_text()
    tc_after = (run_dir / "tc_after.txt").read_text()

    runs.append({
        "name": run_dir.name,
        "valid_router": "10.10.10.128" in traceroute,
        "valid_tc": "delay 60s" in tc_during,
        "valid_cleanup": "fq_codel" in tc_after,
        "latency_applied": "latency_applied=yes" in summary,
        "overall": summarize(rows),
        "baseline": summarize(baseline),
        "fault": summarize(fault_rows),
        "after": summarize(after),
    })

valid_all = all(r["valid_router"] and r["valid_tc"] and r["valid_cleanup"] and r["latency_applied"] for r in runs)

fault_success_rates = [r["fault"]["success_rate"] for r in runs]
fault_error_rates = [r["fault"]["error_rate"] for r in runs]
overall_success_rates = [r["overall"]["success_rate"] for r in runs]
recovery_rates = []
for r in runs:
    text = (SCENARIO / r["name"] / "summary.txt").read_text()
    for line in text.splitlines():
        if line.startswith("recovery_latency_s="):
            try:
                recovery_rates.append(float(line.split("=")[1]))
            except:
                pass

with open(OUT, "w") as f:
    f.write("# Latenztest 1min – verkürzte Messreihe\n\n")
    f.write("## Ziel\n\n")
    f.write("Untersuchung des Verhaltens des HA-K3s-Clusters bei stark erhöhter Netzwerklatenz zwischen Server- und Worker-Netz. Die Latenz wurde auf der Router-VM mittels `tc/netem` eingebracht.\n\n")

    f.write("## Parameter\n\n")
    f.write("| Parameter | Wert |\n|---|---:|\n")
    f.write("| Eingebrachte Latenz | 60s |\n")
    f.write("| Erwartete Round-Trip-Zeit | ca. 120s |\n")
    f.write("| Vorlauf | 180s |\n")
    f.write("| Störphase | 600s |\n")
    f.write("| Nachlauf | 180s |\n")
    f.write("| Wiederholungen | 10 |\n")
    f.write("| HTTP Timeout | 180s |\n")
    f.write("| Request-Intervall | 1s |\n\n")

    f.write("## Validierung\n\n")
    f.write(f"Alle Runs valide: **{'ja' if valid_all else 'nein'}**\n\n")
    f.write("Für jeden Durchlauf wurde geprüft, ob der Netzwerkpfad über die Router-VM `10.10.10.128` verläuft, ob `tc/netem delay 60s` aktiv war und ob nach der Störphase wieder `fq_codel` gesetzt war.\n\n")

    f.write("## Zusammenfassung pro Run\n\n")
    f.write("| Run | Overall Success [%] | Fault Success [%] | Fault Error [%] | Fault Median [ms] | Fault p95 [ms] | >60s | >120s |\n")
    f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
    for r in runs:
        fs = r["fault"]
        f.write(f"| {r['name']} | {fmt(r['overall']['success_rate'])} | {fmt(fs['success_rate'])} | {fmt(fs['error_rate'])} | {fmt(fs['median'])} | {fmt(fs['p95'])} | {fs['gt_60s']} | {fs['gt_120s']} |\n")

    f.write("\n## Aggregierte Metriken\n\n")
    f.write(f"- Overall Request Success Rate: {fmt(stats.mean(overall_success_rates))} %\n")
    f.write(f"- Fault Success Rate Mittelwert: {fmt(stats.mean(fault_success_rates))} %\n")
    f.write(f"- Fault Error Rate Mittelwert: {fmt(stats.mean(fault_error_rates))} %\n")
    if recovery_rates:
        f.write(f"- Recovery Time Mittelwert: {fmt(stats.mean(recovery_rates))} s\n")
        f.write(f"- Recovery Time Minimum: {fmt(min(recovery_rates))} s\n")
        f.write(f"- Recovery Time Maximum: {fmt(max(recovery_rates))} s\n")

    f.write("\n## Interpretation\n\n")
    f.write("Bei einer eingebrachten Latenz von 60s war die Anwendung nicht mehr zuverlässig nutzbar. Während die Baseline- und Nachlaufphase stabile Antwortzeiten im einstelligen Millisekundenbereich zeigten, kam es während der Störphase zu stark verzögerten Requests, Timeouts oder Verbindungsfehlern.\n\n")
    f.write("Die Ergebnisse unterscheiden sich deutlich vom 1s-Latenztest: Dort blieb die Anwendung bei erhöhter Antwortzeit vollständig erreichbar. Bei 60s Latenz treten dagegen bereits deutliche Nutzbarkeitsprobleme auf.\n\n")

    f.write("## Hinweise zur Auswertung\n\n")
    f.write("Für hohe Latenzen ist der Median aller Fault-Requests nur eingeschränkt aussagekräftig, da viele Requests während der Störung abbrechen oder über Phasengrenzen hinweg laufen. Deshalb werden erfolgreiche Requests, Fehlerquote, lange Requests (`>60s`, `>120s`) und Recovery Time gemeinsam betrachtet.\n\n")

    f.write("## Kubernetes-Verhalten\n\n")
    f.write("Die Dateien `nodes_before.txt`, `nodes_after.txt`, `pods_before.txt`, `pods_after.txt`, `events_before.txt` und `events_after.txt` wurden pro Run gespeichert. Sie dienen zur Prüfung von Node-Zuständen, Pod-Restarts und Kubernetes-Events.\n")

print(f"README geschrieben: {OUT}")
