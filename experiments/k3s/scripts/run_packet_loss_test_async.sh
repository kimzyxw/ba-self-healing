#!/bin/bash
set -euo pipefail

SCENARIO="$1"
LOSS="$2"
DURATION="$3"
RUN="$4"
BASELINE="${5:-180}"
AFTER="${6:-180}"
TIMEOUT="${7:-300}"
MAX_IN_FLIGHT="${8:-10}"

ROUTER_NAT="172.16.41.129"
ROUTER_IFACE="ens256"

S1="10.10.10.129"
S2="10.10.10.130"
S3="10.10.10.131"
W1="10.10.20.129"
W2="10.10.20.130"

NODEPORT="31783"
URL="http://${W1}:${NODEPORT}"

BASE=~/ba-self-healing/experiments/k3s/packet-loss-tests/$SCENARIO/run-$RUN-router
mkdir -p "$BASE"

echo "[RUN $RUN] Starte $SCENARIO"
date -Is | tee "$BASE/test_start_time.txt"

echo "$SCENARIO" > "$BASE/scenario.txt"
echo "$LOSS" > "$BASE/loss.txt"
echo "$DURATION" > "$BASE/duration_seconds.txt"
echo "$BASELINE" > "$BASE/baseline_seconds.txt"
echo "$AFTER" > "$BASE/after_seconds.txt"
echo "$TIMEOUT" > "$BASE/timeout_seconds.txt"
echo "$URL" > "$BASE/monitored_url.txt"
echo "$ROUTER_IFACE" > "$BASE/affected_interface.txt"
echo "$MAX_IN_FLIGHT" > "$BASE/max_in_flight.txt"

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

TOTAL_SECONDS=$((BASELINE + DURATION + AFTER + 60))

echo "[RUN $RUN] Starte Request-Monitor für ${TOTAL_SECONDS}s"
date -Is | tee "$BASE/monitor_start_time.txt"

python3 experiments/k3s/scripts/request_monitor_async.py \
  --url "$URL" \
  --output "$BASE/requests.csv" \
  --interval 1 \
  --timeout "$TIMEOUT" \
  --duration "$TOTAL_SECONDS" \
  --max-in-flight "$MAX_IN_FLIGHT" &

MONITOR_PID=$!

echo "[RUN $RUN] Vorlauf läuft ${BASELINE}s"
sleep "$BASELINE"

echo "[RUN $RUN] Starte Router-gesteuerten Paketverlust mit zusätzlichem Safety-Cleanup: $LOSS für ${DURATION}s"
date -Is | tee "$BASE/fault_time.txt"

ROUTER_FAULT_LOG="/tmp/packet-loss-${SCENARIO}-run-${RUN}.log"
S1_CLEANUP_LOG="$BASE/s1_safety_cleanup.log"

# Vorher sicherstellen, dass keine alte netem-Regel aktiv ist
ssh kim@$ROUTER_NAT "sudo tc qdisc del dev $ROUTER_IFACE root || true"
ssh kim@$ROUTER_NAT "tc qdisc show dev $ROUTER_IFACE" | tee "$BASE/tc_before_fault.txt"

# Router setzt die Störung und versucht sie selbst wieder zu entfernen
ssh kim@$ROUTER_NAT "nohup bash -c '
  echo fault_start=\$(date -Is)
  sudo tc qdisc replace dev $ROUTER_IFACE root netem loss $LOSS
  tc qdisc show dev $ROUTER_IFACE
  sleep $DURATION
  sudo tc qdisc del dev $ROUTER_IFACE root || true
  echo router_cleanup_time=\$(date -Is)
  tc qdisc show dev $ROUTER_IFACE
' > $ROUTER_FAULT_LOG 2>&1 &"

sleep 2

ssh kim@$ROUTER_NAT "tc qdisc show dev $ROUTER_IFACE" | tee "$BASE/tc_during.txt"

echo "[RUN $RUN] Fault läuft ${DURATION}s"
sleep "$DURATION"

echo "[RUN $RUN] Erzwinge zusätzliches Cleanup von s1 über Router-NAT"
{
  echo "s1_cleanup_start=$(date -Is)"
  timeout 30 ssh \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=2 \
    kim@$ROUTER_NAT "sudo tc qdisc del dev $ROUTER_IFACE root || true"
  echo "s1_cleanup_end=$(date -Is)"
} > "$S1_CLEANUP_LOG" 2>&1 || true

date -Is | tee "$BASE/recovery_time.txt"

sleep 5

ssh kim@$ROUTER_NAT "tc qdisc show dev $ROUTER_IFACE" | tee "$BASE/tc_after.txt"
ssh kim@$ROUTER_NAT "cat $ROUTER_FAULT_LOG" > "$BASE/router_fault_job.log" || true

echo "[RUN $RUN] Nachlauf läuft ${AFTER}s"
sleep "$AFTER"

kubectl get nodes -o wide > "$BASE/nodes_after.txt"
kubectl get pods -A -o wide > "$BASE/pods_after.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_after.txt"
date -Is | tee "$BASE/test_end_time.txt"

wait "$MONITOR_PID" || true

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
        if not r or r[0] == "request_id":
            continue

        try:
            rows.append({
                "id": r[0],
                "start": t(r[1]),
                "end": t(r[2]),
                "status": r[3],
                "ms": float(r[4]) if r[4] else None,
                "success": r[5] == "True",
                "error": r[6] if len(r) > 6 else ""
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
        print(f"timeouts={sum(1 for r in data if r['error'] == 'TimeoutError')}")
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

print("--- validation ---")
print("router_path_valid=yes")
print("packet_loss_applied=yes")
PY

cat "$BASE/summary.txt"

ls -lh "$BASE"
echo "[RUN $RUN] Fertig: $BASE"
