#!/bin/bash
set -euo pipefail

SCENARIO="$1"
DELAY="$2"
DURATION="$3"

ROUTER_IP="192.168.228.128"
ROUTER_IFACE="ens256"

RUN_SCRIPT=~/ba-self-healing/experiments/k3s/scripts/run_latency_test.sh
LOG=~/ba-self-healing/experiments/k3s/network-tests/$SCENARIO/scenario-run.log

mkdir -p ~/ba-self-healing/experiments/k3s/network-tests/$SCENARIO

echo "Scenario $SCENARIO started at $(date -Is)" | tee -a "$LOG"
echo "Router: $ROUTER_IP interface: $ROUTER_IFACE" | tee -a "$LOG"

for RUN in 01 02 03 04 05 06 07 08 09 10; do
  echo "=== Starting $SCENARIO run-$RUN at $(date -Is) ===" | tee -a "$LOG"

  "$RUN_SCRIPT" \
    "$SCENARIO" \
    "$ROUTER_IP" \
    "$ROUTER_IFACE" \
    "$DELAY" \
    "$DURATION" \
    "$RUN" 2>&1 | tee -a "$LOG"

  echo "=== Finished $SCENARIO run-$RUN at $(date -Is) ===" | tee -a "$LOG"
  sleep 60
done

echo "Scenario $SCENARIO finished at $(date -Is)" | tee -a "$LOG"
