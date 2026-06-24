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

ROUTER_NAT="${ROUTER_NAT:-172.16.41.137}"
ROUTER_IFACE="${ROUTER_IFACE:-ens161}"

C1="10.10.10.133"
E1="10.10.20.131"
E2="10.10.20.132"

URL="${URL:-http://${E1}:30080/}"

BASE=~/ba-self-healing/experiments/kubeedge/packet-loss-tests/$SCENARIO/run-$RUN-router
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
kubectl get pods -n testapp -o wide > "$BASE/testapp_pods_before.txt"
kubectl get pods -A -o wide > "$BASE/pods_before.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_before.txt"

echo "[RUN $RUN] tc-Zustand vor dem Lauf"
ssh kim@$ROUTER_NAT "sudo tc qdisc del dev $ROUTER_IFACE root || true"
ssh kim@$ROUTER_NAT "tc qdisc show dev $ROUTER_IFACE" | tee "$BASE/tc_before_fault.txt"

TOTAL_SECONDS=$((BASELINE + DURATION + AFTER + 60))

echo "[RUN $RUN] Starte async Request-Monitor für ${TOTAL_SECONDS}s"
date -Is | tee "$BASE/monitor_start_time.txt"

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

echo "[RUN $RUN] Starte Router-gesteuerten Paketverlust mit Safety-Cleanup: $LOSS für ${DURATION}s"
date -Is | tee "$BASE/fault_time.txt"

ROUTER_FAULT_LOG="/tmp/kubeedge-packet-loss-${SCENARIO}-run-${RUN}.log"
C1_CLEANUP_LOG="$BASE/c1_safety_cleanup.log"

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

echo "[RUN $RUN] Erzwinge zusätzliches Cleanup von c1 über Router-NAT"
{
  echo "c1_cleanup_start=$(date -Is)"
  timeout 30 ssh \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=2 \
    kim@$ROUTER_NAT "sudo tc qdisc del dev $ROUTER_IFACE root || true"
  echo "c1_cleanup_end=$(date -Is)"
} > "$C1_CLEANUP_LOG" 2>&1 || true

date -Is | tee "$BASE/recovery_time.txt"

sleep 5

ssh kim@$ROUTER_NAT "tc qdisc show dev $ROUTER_IFACE" | tee "$BASE/tc_after.txt"
ssh kim@$ROUTER_NAT "cat $ROUTER_FAULT_LOG" > "$BASE/router_fault_job.log" || true

echo "[RUN $RUN] Nachlauf läuft ${AFTER}s"
sleep "$AFTER"

echo "[RUN $RUN] Route-Preflight nach dem Lauf"
if ~/ba-self-healing/experiments/kubeedge/scripts/verify_kubeedge_routes.sh \
  "$BASE/route_preflight_after"; then
  echo "after_preflight_ok=yes" > "$BASE/after_preflight_status.txt"
else
  echo "WARNING: after preflight failed; continuing so summary and scenario can finish" | tee "$BASE/after_preflight_warning.txt"
  echo "after_preflight_ok=no" > "$BASE/after_preflight_status.txt"
fi

kubectl get nodes -o wide > "$BASE/nodes_after.txt"
kubectl get pods -n testapp -o wide > "$BASE/testapp_pods_after.txt"
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
from collections import Counter

base = Path("$BASE")

def read(name):
    p = base / name
    return p.read_text().strip() if p.exists() else ""

def t(s):
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))

fault = t(read("fault_time.txt"))
recovery = t(read("recovery_time.txt"))

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
    success_vals = sorted(r["ms"] for r in data if r["success"] and r["ms"] is not None)
    fail_vals = sorted(r["ms"] for r in data if not r["success"] and r["ms"] is not None)

    def pct(vals, p):
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
        print(f"p95_ms={pct(vals, 95):.2f}")
        print(f"p99_ms={pct(vals, 99):.2f}")
        print(f"min_ms={min(vals):.2f}")
        print(f"max_ms={max(vals):.2f}")
    else:
        print("latency_values=NA")

    if success_vals:
        print(f"success_median_ms={stats.median(success_vals):.2f}")
        print(f"success_p95_ms={pct(success_vals, 95):.2f}")

    if fail_vals:
        print(f"fail_median_ms={stats.median(fail_vals):.2f}")

    errors = Counter(r["error"] for r in data if r["error"])
    print("errors=" + (";".join(f"{k}:{v}" for k, v in sorted(errors.items())) if errors else "none"))
    print(f"timeouts={errors.get('TimeoutError', 0)}")
    print()

baseline = [r for r in rows if r["start"] < fault]
during = [r for r in rows if fault <= r["start"] < recovery]
after = [r for r in rows if r["start"] >= recovery]

print("=== Run summary ===")
print(f"scenario={base.parent.name}")
print(f"run={base.name}")
print(f"loss={read('loss.txt')}")
print(f"duration_s={read('duration_seconds.txt')}")
print(f"baseline_s={read('baseline_seconds.txt')}")
print(f"after_s={read('after_seconds.txt')}")
print(f"timeout_s={read('timeout_seconds.txt')}")
print(f"max_in_flight={read('max_in_flight.txt')}")
print(f"router_iface={read('affected_interface.txt')}")
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

tc_during = read("tc_during.txt")
tc_after = read("tc_after.txt")
loss = read("loss.txt")

print("--- recovery ---")
print(f"recovery_latency_s={recovered if recovered is not None else 'NA'}")

print("--- validation ---")
print("router_path_valid=yes")
print(f"packet_loss_applied={'yes' if ('netem' in tc_during and ('loss ' + loss) in tc_during) else 'no'}")
print(f"tc_cleanup_documented={'yes' if 'netem' not in tc_after else 'no'}")
PY

cat "$BASE/summary.txt"

ls -lh "$BASE"
echo "[RUN $RUN] Fertig: $BASE"
