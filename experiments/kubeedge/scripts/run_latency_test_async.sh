#!/bin/bash
set -euo pipefail

SCENARIO="$1"
DELAY="$2"
DURATION="$3"
RUN="$4"
BASELINE="${5:-180}"
AFTER="${6:-180}"
TIMEOUT="${7:-300}"
MAX_IN_FLIGHT="${8:-10}"

ROUTER_NAT="172.16.41.137"
ROUTER_IFACES="${ROUTER_IFACES:-ens161}"

C1="10.10.10.133"
E1="10.10.20.131"
E2="10.10.20.132"

URL="${URL:-http://${E1}:30080/}"

BASE=~/ba-self-healing/experiments/kubeedge/latency-tests/$SCENARIO/run-$RUN-router
mkdir -p "$BASE"

echo "[RUN $RUN] Starte $SCENARIO"
date -Is | tee "$BASE/test_start_time.txt"

echo "kubeedge" > "$BASE/system.txt"
echo "$SCENARIO" > "$BASE/scenario.txt"
echo "$DELAY" > "$BASE/delay.txt"
echo "$DURATION" > "$BASE/duration_seconds.txt"
echo "$BASELINE" > "$BASE/baseline_seconds.txt"
echo "$AFTER" > "$BASE/after_seconds.txt"
echo "$TIMEOUT" > "$BASE/timeout_seconds.txt"
echo "$URL" > "$BASE/monitored_url.txt"
echo "$ROUTER_IFACES" > "$BASE/affected_interface.txt"
echo "$MAX_IN_FLIGHT" > "$BASE/max_in_flight.txt"

echo "[RUN $RUN] Route-Preflight vor dem Lauf"
~/ba-self-healing/experiments/kubeedge/scripts/verify_kubeedge_routes.sh \
  "$BASE/route_preflight_before"

echo "[RUN $RUN] Validiere Routerpfad"
traceroute "$E1" | tee "$BASE/traceroute_before.txt"

if ! grep -q "10.10.10.136" "$BASE/traceroute_before.txt"; then
  echo "[RUN $RUN] FEHLER: Routerpfad nicht korrekt"
  exit 1
fi

echo "[RUN $RUN] Kubernetes-Zustand vor dem Lauf"
kubectl get nodes -o wide > "$BASE/nodes_before.txt"
kubectl get pods -A -o wide > "$BASE/pods_before.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_before.txt"

echo "[RUN $RUN] tc-Zustand vor dem Lauf"
for IFACE in $ROUTER_IFACES; do
  echo "===== $IFACE =====" | tee -a "$BASE/tc_before.txt"
  ssh kim@$ROUTER_NAT "tc qdisc show dev $IFACE" | tee -a "$BASE/tc_before.txt"
done

TOTAL_SECONDS=$((BASELINE + DURATION + AFTER))

echo "[RUN $RUN] Starte async Request-Monitor für ${TOTAL_SECONDS}s"
python3 experiments/kubeedge/scripts/request_monitor_async.py \
  --url "$URL" \
  --output "$BASE/requests.csv" \
  --interval 1 \
  --timeout "$TIMEOUT" \
  --duration "$TOTAL_SECONDS" \
  --max-in-flight "$MAX_IN_FLIGHT" &

MONITOR_PID=$!

echo "[RUN $RUN] Vorlauf läuft ${BASELINE}s"
sleep "$BASELINE"

echo "[RUN $RUN] Setze Latenz: $DELAY auf Router-Interfaces $ROUTER_IFACES"
date -Is | tee "$BASE/fault_time.txt"
for IFACE in $ROUTER_IFACES; do
  ssh kim@$ROUTER_NAT "sudo tc qdisc replace dev $IFACE root netem delay $DELAY"
  echo "===== $IFACE =====" | tee -a "$BASE/tc_during.txt"
  ssh kim@$ROUTER_NAT "tc qdisc show dev $IFACE" | tee -a "$BASE/tc_during.txt"
done

echo "[RUN $RUN] Störphase läuft ${DURATION}s"
sleep "$DURATION"

echo "[RUN $RUN] Entferne Latenz"
date -Is | tee "$BASE/recovery_time.txt"
for IFACE in $ROUTER_IFACES; do
  ssh kim@$ROUTER_NAT "sudo tc qdisc del dev $IFACE root || true"
  echo "===== $IFACE =====" | tee -a "$BASE/tc_after.txt"
  ssh kim@$ROUTER_NAT "tc qdisc show dev $IFACE" | tee -a "$BASE/tc_after.txt"
done

echo "[RUN $RUN] Nachlauf läuft ${AFTER}s"
sleep "$AFTER"

echo "[RUN $RUN] Kubernetes-Zustand nach dem Lauf"
kubectl get nodes -o wide > "$BASE/nodes_after.txt"
kubectl get pods -A -o wide > "$BASE/pods_after.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_after.txt"
date -Is | tee "$BASE/test_end_time.txt"

wait "$MONITOR_PID" || true

echo "[RUN $RUN] Route-Preflight nach dem Lauf"
if ~/ba-self-healing/experiments/kubeedge/scripts/verify_kubeedge_routes.sh \
  "$BASE/route_preflight_after"; then
  echo "after_preflight_ok=yes" > "$BASE/after_preflight_status.txt"
else
  echo "WARNING: after preflight failed; continuing so summary and scenario can finish" | tee "$BASE/after_preflight_warning.txt"
  echo "after_preflight_ok=no" > "$BASE/after_preflight_status.txt"
fi

echo "[RUN $RUN] Berechne Zusammenfassung"

python3 - <<PY | tee "$BASE/summary.txt"
import csv
from pathlib import Path
from datetime import datetime
import statistics as stats
from collections import Counter

base = Path("$BASE")
delay = "$DELAY"
router_iface = "$ROUTER_IFACES"

def t(s):
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))

def pct(vals, p):
    if not vals:
        return None
    vals = sorted(vals)
    return vals[min(int(len(vals) * p / 100), len(vals) - 1)]

def fmt(v):
    return "NA" if v is None else f"{v:.2f}"

fault = t((base / "fault_time.txt").read_text())
recovery = t((base / "recovery_time.txt").read_text())

rows = []
with open(base / "requests.csv", newline="") as f:
    reader = csv.DictReader(f)
    for r in reader:
        try:
            rows.append({
                "id": r.get("request_id", ""),
                "start": t(r["request_start_time"]),
                "end": t(r["request_end_time"]),
                "status": r.get("status_code", ""),
                "ms": float(r["duration_ms"]) if r.get("duration_ms") else None,
                "success": r.get("success") == "True",
                "error": r.get("error", ""),
            })
        except Exception:
            pass

def section(name, data):
    total = len(data)
    ok = sum(1 for r in data if r["success"])
    fail = total - ok
    vals = sorted(r["ms"] for r in data if r["ms"] is not None)
    success_vals = sorted(r["ms"] for r in data if r["success"] and r["ms"] is not None)
    errors = Counter(r["error"] or "unknown" for r in data if not r["success"])

    print(f"--- {name} ---")
    print(f"requests_total={total}")
    print(f"success={ok}")
    print(f"failed={fail}")
    print(f"success_rate={ok / total * 100:.2f}%" if total else "success_rate=NA")
    print(f"error_rate={fail / total * 100:.2f}%" if total else "error_rate=NA")

    if vals:
        print(f"avg_ms={stats.mean(vals):.2f}")
        print(f"median_ms={stats.median(vals):.2f}")
        print(f"p95_ms={fmt(pct(vals, 95))}")
        print(f"p99_ms={fmt(pct(vals, 99))}")
        print(f"min_ms={min(vals):.2f}")
        print(f"max_ms={max(vals):.2f}")
        print(f"outliers_gt_10s={sum(v > 10000 for v in vals)}")
        print(f"outliers_gt_60s={sum(v > 60000 for v in vals)}")
        print(f"outliers_gt_120s={sum(v > 120000 for v in vals)}")
        print(f"outliers_gt_300s={sum(v > 300000 for v in vals)}")
    else:
        print("latency_values=NA")

    if success_vals:
        print(f"success_median_ms={stats.median(success_vals):.2f}")
        print(f"success_p95_ms={fmt(pct(success_vals, 95))}")

    if errors:
        print("errors=" + ";".join(f"{k}:{v}" for k, v in sorted(errors.items())))
    else:
        print("errors=none")
    print()

baseline = [r for r in rows if r["start"] < fault]
during = [r for r in rows if fault <= r["start"] < recovery]
after = [r for r in rows if r["start"] >= recovery]

print("=== Run summary ===")
print("system=kubeedge")
print(f"scenario={base.parent.name}")
print(f"run={base.name}")
print(f"url={(base / 'monitored_url.txt').read_text().strip()}")
print(f"delay={delay}")
print(f"router_ifaces={router_iface}")
print(f"fault_time={fault.isoformat()}")
print(f"recovery_time={recovery.isoformat()}")
print()

section("overall", rows)
section("baseline", baseline)
section("fault", during)
section("after", after)

recovered = None
for r in after:
    if r["success"] and r["ms"] is not None and r["ms"] < 500:
        recovered = (r["end"] - recovery).total_seconds()
        break

print("--- recovery ---")
print(f"recovery_latency_s={recovered if recovered is not None else 'NA'}")

traceroute = (base / "traceroute_before.txt").read_text(errors="replace") if (base / "traceroute_before.txt").exists() else ""
tc_during = (base / "tc_during.txt").read_text(errors="replace") if (base / "tc_during.txt").exists() else ""
tc_after = (base / "tc_after.txt").read_text(errors="replace") if (base / "tc_after.txt").exists() else ""

fault_vals = [r["ms"] for r in during if r["ms"] is not None]
median_fault = stats.median(fault_vals) if fault_vals else None

print("--- validation ---")
print("router_path_valid=yes" if "10.10.10.136" in traceroute else "router_path_valid=no")
print("tc_active=yes" if "netem" in tc_during and delay in tc_during else "tc_active=no")
print("tc_cleanup_documented=yes" if "netem" not in tc_after else "tc_cleanup_documented=no")
print(f"fault_median_ms={fmt(median_fault)}")
print("latency_applied=yes" if median_fault is not None and median_fault > 1000 else "latency_applied=check")
PY

cat "$BASE/summary.txt"

ls -lh "$BASE"
echo "[RUN $RUN] Fertig: $BASE"
