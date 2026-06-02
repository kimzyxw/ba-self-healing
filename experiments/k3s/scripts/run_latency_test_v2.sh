#!/bin/bash
set -euo pipefail

SCENARIO="$1"
DELAY="$2"
DURATION="$3"
RUN="$4"
BASELINE="${5:-300}"
AFTER="${6:-300}"

ROUTER_NAT="10.10.10.128"
ROUTER_IFACE="ens256"

S1="10.10.10.129"
S2="10.10.10.130"
S3="10.10.10.131"
W1="10.10.20.129"
W2="10.10.20.130"

NODEPORT="31783"
URL="http://${W1}:${NODEPORT}"

BASE=~/ba-self-healing/experiments/k3s/network-tests/$SCENARIO/run-$RUN-router
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
  --timeout 10 &
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

ls -lh "$BASE"
echo "[RUN $RUN] Fertig: $BASE"
