#!/bin/bash
set -euo pipefail

SCENARIO="$1"
DELAY="$2"
DURATION="$3"
RUN="$4"
BASELINE="${5:-300}"
AFTER="${6:-300}"

ROUTER_NAT="172.16.41.129"
ROUTER_IFACE="ens256"

S1="10.10.10.129"
S2="10.10.10.130"
S3="10.10.10.131"
W1="10.10.20.129"
W2="10.10.20.130"

NODEPORT="31783"
URL="http://${W1}:${NODEPORT}"

BASE=~/ba-self-healing/experiments/k3s/latency-tests/$SCENARIO/run-$RUN-router
mkdir -p "$BASE"

echo "[RUN $RUN] Starte $SCENARIO"
date -Is | tee "$BASE/test_start_time.txt"

echo "$SCENARIO" > "$BASE/scenario.txt"
echo "$DELAY" > "$BASE/delay.txt"
echo "$DURATION" > "$BASE/duration_seconds.txt"
echo "$BASELINE" > "$BASE/baseline_seconds.txt"
echo "$AFTER" > "$BASE/after_seconds.txt"
echo "$URL" > "$BASE/monitored_url.txt"
echo "$ROUTER_IFACE" > "$BASE/affected_interface.txt"

echo "[RUN $RUN] Setze Routen und aktiviere ip_forward"
ssh kim@$ROUTER_NAT "sudo sysctl -w net.ipv4.ip_forward=1"

for node in "$S1" "$S2" "$S3"; do
  ssh kim@$node "sudo ip route replace 10.10.20.0/24 via 10.10.10.128"
done

for node in "$W1" "$W2"; do
  ssh kim@$node "sudo ip route replace 10.10.10.0/24 via 10.10.20.128"
done

echo "[RUN $RUN] Validiere Routerpfad"
traceroute "$W1" | tee "$BASE/traceroute_before.txt"

if ! grep -q "10.10.10.128" "$BASE/traceroute_before.txt"; then
  echo "[RUN $RUN] FEHLER: Routerpfad nicht korrekt"
  exit 1
fi

kubectl get nodes -o wide > "$BASE/nodes_before.txt"
kubectl get pods -A -o wide > "$BASE/pods_before.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_before.txt"

python3 ~/ba-self-healing/experiments/k3s/scripts/request_monitor.py \
  --url "$URL" \
  --output "$BASE/requests.csv" \
  --interval 1 \
  --timeout 180 &
MONITOR_PID=$!

echo "[RUN $RUN] Vorlauf läuft ${BASELINE}s"
sleep "$BASELINE"

echo "[RUN $RUN] Setze Latenz: $DELAY"
date -Is | tee "$BASE/fault_time.txt"
ssh kim@$ROUTER_NAT "sudo tc qdisc replace dev $ROUTER_IFACE root netem delay $DELAY"
ssh kim@$ROUTER_NAT "tc qdisc show dev $ROUTER_IFACE" | tee "$BASE/tc_during.txt"

sleep "$DURATION"

echo "[RUN $RUN] Entferne Latenz"
date -Is | tee "$BASE/recovery_time.txt"
ssh kim@$ROUTER_NAT "sudo tc qdisc del dev $ROUTER_IFACE root || true"
ssh kim@$ROUTER_NAT "tc qdisc show dev $ROUTER_IFACE" | tee "$BASE/tc_after.txt"

echo "[RUN $RUN] Nachlauf läuft ${AFTER}s"
sleep "$AFTER"

kubectl get nodes -o wide > "$BASE/nodes_after.txt"
kubectl get pods -A -o wide > "$BASE/pods_after.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_after.txt"
date -Is | tee "$BASE/test_end_time.txt"

kill "$MONITOR_PID" || true

echo "[RUN $RUN] Berechne Zusammenfassung"

python3 - <<PY | tee "$BASE/summary.txt"
import csv
from pathlib import Path
from datetime import datetime
import statistics as stats

base = Path("$BASE")

def t(s):
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))

fault = t((base / "fault_time.txt").read_text())
recovery = t((base / "recovery_time.txt").read_text())

rows = []
with open(base / "requests.csv", newline="") as f:
    reader = csv.reader(f)
    for r in reader:
        if not r or r[0] == "timestamp":
            continue
        try:
            rows.append({
		"start": t(r[0]),
		"end": t(r[1]),
		"status": r[2],
		"ms": float(r[3]) if r[3] else None,
		"success": r[4] == "True",
		"error": r[5] if len(r) > 5 else ""
            })
        except Exception:
            pass

def section(name, data):
    total = len(data)
    ok = sum(1 for r in data if r["success"])
    fail = total - ok
    vals = sorted(r["ms"] for r in data if r["ms"] is not None)

    def pct(p):
        if not vals:
            return None
        return vals[min(int(len(vals) * p / 100), len(vals) - 1)]

    print(f"--- {name} ---")
    print(f"requests_total={total}")
    print(f"success={ok}")
    print(f"failed={fail}")
    print(f"success_rate={ok / total * 100:.2f}%" if total else "success_rate=NA")
    print(f"error_rate={fail / total * 100:.2f}%" if total else "error_rate=NA")

    if vals:
        print(f"avg_ms={stats.mean(vals):.2f}")
        print(f"median_ms={stats.median(vals):.2f}")
        print(f"p95_ms={pct(95):.2f}")
        print(f"p99_ms={pct(99):.2f}")
        print(f"min_ms={min(vals):.2f}")
        print(f"max_ms={max(vals):.2f}")
        print(f"outliers_gt_10s={sum(v > 10000 for v in vals)}")
    else:
        print("latency_values=NA")
    print()

baseline = [r for r in rows if r["start"] < fault]
during = [r for r in rows if fault <= r["start"] < recovery]
after = [r for r in rows if r["start"] >= recovery]

print("=== Run summary ===")
print(f"scenario={base.parent.name}")
print(f"run={base.name}")
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

fault_vals = [r["ms"] for r in during if r["ms"] is not None]
if fault_vals:
    median_fault = stats.median(fault_vals)
    print("--- validation ---")
    print("router_path_valid=yes")
    print(f"fault_median_ms={median_fault:.2f}")
    print("latency_applied=yes" if median_fault > 1500 else "latency_applied=no")
PY

cat "$BASE/summary.txt"

ls -lh "$BASE"
echo "[RUN $RUN] Fertig: $BASE"
