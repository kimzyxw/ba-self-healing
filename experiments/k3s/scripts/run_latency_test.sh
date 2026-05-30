#!/bin/bash
set -euo pipefail

SCENARIO="$1"
ROUTER_IP="$2"
ROUTER_IFACE="$3"
DELAY="$4"
DURATION="$5"
RUN="$6"

BASE=~/ba-self-healing/experiments/k3s/network-tests/$SCENARIO/run-$RUN-router
mkdir -p "$BASE"

date -Is | tee "$BASE/test_start_time.txt"
echo "router" | tee "$BASE/affected_node.txt"
echo "$ROUTER_IP" | tee "$BASE/affected_router_ip.txt"
echo "$ROUTER_IFACE" | tee "$BASE/affected_interface.txt"
echo "$SCENARIO" | tee "$BASE/scenario.txt"
echo "tc netem delay $DELAY for $DURATION seconds on router interface $ROUTER_IFACE" | tee "$BASE/fault_method.txt"

sudo kubectl get nodes -o wide > "$BASE/nodes_before.txt"
sudo kubectl get pods -A -o wide > "$BASE/pods_before.txt"
sudo kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_before.txt"

python3 ~/ba-self-healing/experiments/k3s/scripts/request_monitor.py \
  --url http://192.168.228.130:30243 \
  --output "$BASE/requests.csv" \
  --interval 1 \
  --timeout 5 &
MONITOR_PID=$!

echo "[RUN $RUN] Baseline läuft 5 Minuten"

sleep 300

date -Is | tee "$BASE/fault_time.txt"
ssh -t kim@"$ROUTER_IP" "sudo tc qdisc replace dev $ROUTER_IFACE root netem delay $DELAY"

sleep "$DURATION"

date -Is | tee "$BASE/recovery_time.txt"
ssh -t kim@"$ROUTER_IP" "sudo tc qdisc del dev $ROUTER_IFACE root || true"

sleep 300

sudo kubectl get nodes -o wide > "$BASE/nodes_after.txt"
sudo kubectl get pods -A -o wide > "$BASE/pods_after.txt"
sudo kubectl get events -A --sort-by=.metadata.creationTimestamp > "$BASE/events_after.txt"
date -Is | tee "$BASE/test_end_time.txt"

kill "$MONITOR_PID" || true

ls -lh "$BASE"

echo "[RUN $RUN] Fertig: $BASE"
