#!/bin/bash
set -euo pipefail

SCENARIO="$1"
DURATION="$2"
RUN="$3"
BASELINE="${4:-180}"
AFTER="${5:-180}"
TIMEOUT="${6:-300}"
MAX_IN_FLIGHT="${7:-10}"

ROUTER_NAT="${ROUTER_NAT:-172.16.41.137}"
ROUTER_IFACE="${ROUTER_IFACE:-ens161}"

C1="10.10.10.133"
C2="10.10.10.134"
C3="10.10.10.135"
E1="10.10.20.131"
E2="10.10.20.132"

CLOUD_GW="10.10.10.136"
EDGE_GW="10.10.20.133"

URL="${URL:-http://${E1}:30080/}"

BASE=~/ba-self-healing/experiments/kubeedge/link-cut-tests/$SCENARIO/run-$RUN-router
mkdir -p "$BASE"

echo "[RUN $RUN] Starte $SCENARIO"
date -Is | tee "$BASE/test_start_time.txt"

echo "$SCENARIO" > "$BASE/scenario.txt"
echo "$DURATION" > "$BASE/duration_seconds.txt"
echo "$BASELINE" > "$BASE/baseline_seconds.txt"
echo "$AFTER" > "$BASE/after_seconds.txt"
echo "$TIMEOUT" > "$BASE/timeout_seconds.txt"
echo "$URL" > "$BASE/monitored_url.txt"
echo "$ROUTER_IFACE" > "$BASE/affected_interface.txt"
echo "$MAX_IN_FLIGHT" > "$BASE/max_in_flight.txt"
echo "ip_link_down_up" > "$BASE/fault_type.txt"

echo "[RUN $RUN] Aktiviere ip_forward auf Router"
ssh kim@$ROUTER_NAT "sudo -n sysctl -w net.ipv4.ip_forward=1"

# Die statischen Routen wurden beim Clusteraufbau eingerichtet.
# Standardmäßig werden sie hier nur validiert, nicht neu gesetzt.
# Optional kann REFRESH_ROUTES=1 gesetzt werden, falls die Routen vor einem Lauf neu geschrieben werden sollen.
if [ "${REFRESH_ROUTES:-0}" = "1" ]; then
  echo "[RUN $RUN] REFRESH_ROUTES=1: Setze Routen auf Cloud- und Edge-Nodes neu"
  for node in "$C1" "$C2" "$C3"; do
    ssh kim@$node "sudo -n ip route replace 10.10.20.0/24 via $CLOUD_GW"
  done

  for node in "$E1" "$E2"; do
    ssh kim@$node "sudo -n ip route replace 10.10.10.0/24 via $EDGE_GW"
  done
else
  echo "[RUN $RUN] REFRESH_ROUTES=0: Überspringe Route-Refresh, validiere vorhandene Routen"
fi

echo "[RUN $RUN] Validiere Routerpfad"
traceroute "$E1" | tee "$BASE/traceroute_before.txt"

if ! grep -q "$CLOUD_GW" "$BASE/traceroute_before.txt"; then
  echo "[RUN $RUN] FEHLER: Routerpfad nicht korrekt"
  exit 1
fi

if [ -x experiments/kubeedge/scripts/verify_kubeedge_routes.sh ]; then
  experiments/kubeedge/scripts/verify_kubeedge_routes.sh > "$BASE/verify_routes_before.txt" 2>&1 || true
fi

kubectl get nodes -o wide > "$BASE/nodes_before.txt"
kubectl get pods -A -o wide > "$BASE/pods_before.txt"
kubectl get pods -n testapp -o wide > "$BASE/testapp_pods_before.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_before.txt"

MONITOR_BUFFER=1800
TOTAL_SECONDS=$((BASELINE + DURATION + AFTER + MONITOR_BUFFER))

echo "[RUN $RUN] Starte Request-Monitor für ${TOTAL_SECONDS}s"
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

echo "[RUN $RUN] Starte Verbindungsabbruch auf Router-Interface $ROUTER_IFACE für ${DURATION}s"
date -Is | tee "$BASE/fault_time.txt"

ROUTER_FAULT_LOG="/tmp/kubeedge-link-cut-${SCENARIO}-run-${RUN}.log"
ROUTER_DURING_FILE="/tmp/kubeedge-link-cut-${SCENARIO}-run-${RUN}-during.txt"
ROUTER_AFTER_FILE="/tmp/kubeedge-link-cut-${SCENARIO}-run-${RUN}-after.txt"
SAFETY_CLEANUP_LOG="$BASE/c1_safety_cleanup.log"

ssh kim@$ROUTER_NAT "sudo -n ip link show dev $ROUTER_IFACE" > "$BASE/interface_before_fault.txt"

ssh kim@$ROUTER_NAT "rm -f $ROUTER_FAULT_LOG $ROUTER_DURING_FILE $ROUTER_AFTER_FILE"

ssh kim@$ROUTER_NAT "nohup bash -c '
  echo fault_start=\$(date -Is)
  sudo -n ip link set dev $ROUTER_IFACE down
  sudo -n ip link show dev $ROUTER_IFACE | tee $ROUTER_DURING_FILE
  sleep $DURATION
  sudo -n ip link set dev $ROUTER_IFACE up
  echo router_recovery_time=\$(date -Is)
  sudo -n ip link show dev $ROUTER_IFACE | tee $ROUTER_AFTER_FILE
' > $ROUTER_FAULT_LOG 2>&1 &"

sleep 0.2

ssh kim@$ROUTER_NAT "cat $ROUTER_DURING_FILE 2>/dev/null || sudo -n ip link show dev $ROUTER_IFACE" > "$BASE/interface_during_fault.txt" || true

echo "[RUN $RUN] Verbindungsabbruch läuft ${DURATION}s"
sleep "$DURATION"

echo "[RUN $RUN] Erzwinge zusätzliches Interface-Up über Router-NAT"
{
  echo "safety_cleanup_start=$(date -Is)"
  timeout 30 ssh \
    -o ConnectTimeout=10 \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=2 \
    kim@$ROUTER_NAT "sudo -n ip link set dev $ROUTER_IFACE up"
  echo "safety_cleanup_end=$(date -Is)"
} > "$SAFETY_CLEANUP_LOG" 2>&1 || true

date -Is | tee "$BASE/recovery_time.txt"

sleep 5

ssh kim@$ROUTER_NAT "cat $ROUTER_AFTER_FILE 2>/dev/null || sudo -n ip link show dev $ROUTER_IFACE" > "$BASE/interface_after_fault.txt"
ssh kim@$ROUTER_NAT "cat $ROUTER_FAULT_LOG" > "$BASE/router_fault_job.log" || true

if [ -x experiments/kubeedge/scripts/verify_kubeedge_routes.sh ]; then
  experiments/kubeedge/scripts/verify_kubeedge_routes.sh > "$BASE/verify_routes_after.txt" 2>&1 || true
fi

echo "[RUN $RUN] Nachlauf läuft ${AFTER}s"
sleep "$AFTER"

kubectl get nodes -o wide > "$BASE/nodes_after.txt"
kubectl get pods -A -o wide > "$BASE/pods_after.txt"
kubectl get pods -n testapp -o wide > "$BASE/testapp_pods_after.txt"
kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_after.txt"

curl -m 5 -s -o /dev/null -w "after_preflight_http_code=%{http_code}\n" "$URL" > "$BASE/after_preflight_status.txt" || echo "after_preflight_http_code=000" > "$BASE/after_preflight_status.txt"

date -Is | tee "$BASE/test_end_time.txt"

echo "[RUN $RUN] Stoppe Request-Monitor nach geplantem Testende"
date -Is | tee "$BASE/monitor_stop_time.txt"

if kill -0 "$MONITOR_PID" 2>/dev/null; then
  kill "$MONITOR_PID" 2>/dev/null || true
  wait "$MONITOR_PID" || true
else
  echo "[RUN $RUN] Request-Monitor war bereits beendet" | tee "$BASE/monitor_already_finished.txt"
fi

echo "[RUN $RUN] Berechne Zusammenfassung"

python3 - <<PY | tee "$BASE/summary.txt"
import csv
from pathlib import Path
from datetime import datetime
import statistics as stats
from collections import Counter

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
    ok_vals = sorted(r["ms"] for r in data if r["success"] and r["ms"] is not None)
    errors = Counter(r["error"] for r in data if not r["success"] and r["error"])

    def pct(values, p):
        if not values:
            return None
        return values[min(int(len(values) * p / 100), len(values) - 1)]

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

    if ok_vals:
        print(f"success_median_ms={stats.median(ok_vals):.2f}")
        print(f"success_p95_ms={pct(ok_vals, 95):.2f}")

    print("errors=" + (";".join(f"{k}:{v}" for k, v in errors.items()) if errors else "none"))
    print(f"timeouts={sum(1 for r in data if r['error'] == 'TimeoutError')}")
    print()

baseline = [r for r in rows if r["start"] < fault]
during = [r for r in rows if fault <= r["start"] < recovery]
after = [r for r in rows if r["start"] >= recovery]

print("=== Run summary ===")
print(f"scenario={base.parent.name}")
print(f"run={base.name}")
print(f"fault_time={fault.isoformat()}")
print(f"recovery_time={recovery.isoformat()}")
print(f"fault_type=ip_link_down_up")
print(f"router_iface=$ROUTER_IFACE")
print(f"duration_s=$DURATION")
print(f"baseline_s=$BASELINE")
print(f"after_s=$AFTER")
print(f"timeout_s=$TIMEOUT")
print(f"max_in_flight=$MAX_IN_FLIGHT")
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

before = (base / "interface_before_fault.txt").read_text(errors="ignore") if (base / "interface_before_fault.txt").exists() else ""
during_txt = (base / "interface_during_fault.txt").read_text(errors="ignore") if (base / "interface_during_fault.txt").exists() else ""
after_txt = (base / "interface_after_fault.txt").read_text(errors="ignore") if (base / "interface_after_fault.txt").exists() else ""
router_log = (base / "router_fault_job.log").read_text(errors="ignore") if (base / "router_fault_job.log").exists() else ""

router_path_valid = "yes" if "$CLOUD_GW" in (base / "traceroute_before.txt").read_text(errors="ignore") else "no"
link_cut_applied = "yes" if (
    "state DOWN" in during_txt
    or "NO-CARRIER" in during_txt
    or "state DOWN" in router_log
) else "no"
interface_recovered = "yes" if ("state UP" in after_txt and "LOWER_UP" in after_txt) else "no"
router_recovery_documented = "yes" if "router_recovery_time=" in router_log else "no"

print("--- recovery ---")
print(f"recovery_latency_s={recovered if recovered is not None else 'NA'}")

print("--- validation ---")
print(f"router_path_valid={router_path_valid}")
print(f"link_cut_applied={link_cut_applied}")
print(f"interface_recovered={interface_recovered}")
print(f"router_recovery_documented={router_recovery_documented}")
PY

cat "$BASE/summary.txt"

ls -lh "$BASE"
echo "[RUN $RUN] Fertig: $BASE"
